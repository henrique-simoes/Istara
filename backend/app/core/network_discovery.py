"""Network discovery for LLM servers on the local network.

Scans the local subnet for LM Studio (port 1234) and Ollama (port 11434)
instances, then registers any found servers with the LLM Router.
"""

import asyncio
import logging
import socket
import time

import httpx

logger = logging.getLogger(__name__)

# Ports to probe for LLM servers
DISCOVERY_PORTS = [
    (1234, "lmstudio", "/v1/models"),       # LM Studio
    (11434, "ollama", "/api/tags"),           # Ollama
    (8080, "openai_compat", "/v1/models"),   # Common OpenAI-compat
]

# Timeout for each probe (seconds)
PROBE_TIMEOUT = 1.5

# Max concurrent probes to avoid flooding the network
MAX_CONCURRENT = 50


def _get_local_subnets() -> list[str]:
    """Get local /24 subnets from active network interfaces."""
    subnets = set()
    try:
        hostname = socket.gethostname()
        local_ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for info in local_ips:
            ip = info[4][0]
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            parts = ip.split(".")
            subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
            subnets.add(subnet)
    except Exception:
        pass

    # Also try getting IPs via socket connection trick
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split(".")
        subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
        subnets.add(subnet)
    except Exception:
        pass

    return list(subnets)


def _get_local_ips() -> set[str]:
    """Get all local IP addresses to exclude from scanning."""
    local = {"127.0.0.1", "localhost"}
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            local.add(info[4][0])
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        local.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return local


async def _probe_host(client: httpx.AsyncClient, ip: str, port: int, provider_type: str, endpoint: str) -> dict | None:
    """Probe a single host:port for an LLM server. Returns server info or None."""
    url = f"http://{ip}:{port}{endpoint}"
    try:
        resp = await client.get(url, timeout=PROBE_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Extract model names
            models = []
            if provider_type == "ollama":
                models = [m.get("name", "") for m in data.get("models", [])]
            else:
                models = [m.get("id", "") for m in data.get("data", [])]

            return {
                "ip": ip,
                "port": port,
                "provider_type": provider_type,
                "host": f"http://{ip}:{port}",
                "models": models,
                "name": f"Network {provider_type.replace('_', ' ').title()} ({ip})",
            }
    except Exception:
        pass
    return None


async def discover_network_servers(
    extra_hosts: list[str] | None = None,
    skip_local: bool = True,
) -> list[dict]:
    """Scan local network for LLM servers.

    Returns a list of discovered server dicts with keys:
        ip, port, provider_type, host, models, name

    Args:
        extra_hosts: Additional IPs/hostnames to probe beyond subnet scan.
        skip_local: If True, skip the local machine's IPs.
    """
    discovered = []
    local_ips = _get_local_ips() if skip_local else set()
    subnets = _get_local_subnets()

    if not subnets:
        logger.warning("No local subnets found for network discovery")
        return discovered

    logger.info(f"Network discovery: scanning subnets {subnets}")

    # Build list of (ip, port, provider_type, endpoint) tuples to probe
    targets = []
    for subnet in subnets:
        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            if ip in local_ips:
                continue
            for port, ptype, endpoint in DISCOVERY_PORTS:
                targets.append((ip, port, ptype, endpoint))

    # Add extra hosts
    if extra_hosts:
        for host in extra_hosts:
            for port, ptype, endpoint in DISCOVERY_PORTS:
                targets.append((host, port, ptype, endpoint))

    # Probe all targets with concurrency limit
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    start = time.time()

    async with httpx.AsyncClient() as client:
        async def limited_probe(ip, port, ptype, endpoint):
            async with semaphore:
                return await _probe_host(client, ip, port, ptype, endpoint)

        tasks = [limited_probe(ip, port, ptype, ep) for ip, port, ptype, ep in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, dict) and result is not None:
            discovered.append(result)

    elapsed = time.time() - start
    logger.info(f"Network discovery complete: found {len(discovered)} servers in {elapsed:.1f}s")

    return discovered


async def discover_and_register() -> list[dict]:
    """Discover network LLM servers and register them with the LLM Router.

    Called at startup and can be called on-demand via API.
    Returns list of newly registered servers.
    """
    from app.core.llm_router import llm_router, LLMServerEntry

    discovered = await discover_network_servers()
    newly_registered = []

    for server_info in discovered:
        server_id = f"discovered-{server_info['ip']}-{server_info['port']}"

        # Skip if already registered
        if server_id in llm_router._servers:
            continue

        entry = LLMServerEntry(
            server_id=server_id,
            name=server_info["name"],
            provider_type=server_info["provider_type"],
            host=server_info["host"],
            priority=10,  # Higher priority than fallback (5) but lower than local (1)
            is_local=False,
        )
        entry.is_healthy = True  # Already confirmed reachable

        llm_router.register_server(entry)
        newly_registered.append(server_info)
        logger.info(f"Auto-discovered LLM server: {server_info['name']} with models: {server_info['models']}")

    # Persist discovered servers to database
    if newly_registered:
        try:
            import uuid
            import json
            from app.models.database import async_session
            from app.models.llm_server import LLMServer

            async with async_session() as db:
                from sqlalchemy import select
                for info in newly_registered:
                    # Check if already in DB
                    result = await db.execute(
                        select(LLMServer).where(LLMServer.host == info["host"])
                    )
                    if result.scalar_one_or_none():
                        continue

                    server = LLMServer(
                        id=str(uuid.uuid4()),
                        name=info["name"],
                        provider_type=info["provider_type"],
                        host=info["host"],
                        is_local=False,
                        is_healthy=True,
                        priority=10,
                        capabilities=json.dumps({
                            "discovered": True,
                            "models": info["models"],
                            "discovery_method": "network_scan",
                        }),
                    )
                    db.add(server)
                await db.commit()
                logger.info(f"Persisted {len(newly_registered)} discovered servers to database")
        except Exception as e:
            logger.warning(f"Failed to persist discovered servers: {e}")

    return newly_registered
