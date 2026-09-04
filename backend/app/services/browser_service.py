"""Browser automation service — wraps browser-use for agent-driven web browsing.

Uses browser-use library with LM Studio/Ollama as the LLM provider.
Compatible with any OpenAI-compatible endpoint via langchain_openai.ChatOpenAI.

W2 (master plan §8): endpoint identity no longer comes from raw settings —
``_resolve_browser_endpoint`` resolves the matching LOCAL entry of the Pi
catalog (``PiModelManager``), and every run records one governed row in the
agentic usage ledger under ``tool.browse_website``. browser-use still drives
its own agent loop (it needs a live LangChain LLM object); only the routing
identity and accounting moved onto the governed plane.

Install: pip install browser-use langchain-openai
"""

import logging
import time

from app.config import settings
from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.model_manager import PiModelManager

logger = logging.getLogger(__name__)

BROWSER_AVAILABLE = False
try:
    from browser_use import Agent as BrowserAgent
    from browser_use import Browser, BrowserConfig
    from langchain_openai import ChatOpenAI

    BROWSER_AVAILABLE = True
except ImportError:
    logger.info(
        "browser-use not installed — browse_website tool unavailable. "
        "Install: pip install browser-use langchain-openai"
    )


def _resolve_browser_endpoint() -> ResolvedPiEndpoint:
    """Resolve the browser tool's endpoint identity from the Pi catalog (W2).

    Maps the configured provider onto the corresponding LOCAL Pi catalog
    entry: ``pi-local-lmstudio`` / ``pi-local-ollama`` carry the same hosts,
    models, and keys the old raw-settings construction used, so routing is
    unchanged while identity now comes from the Pi plane. An unknown provider
    keeps the old LM Studio guess. Resolution fails closed
    (``PiEndpointResolutionError``) rather than falling back to raw settings.
    """
    provider = (settings.llm_provider or "").strip().lower()
    endpoint_id = {
        "lmstudio": "pi-local-lmstudio",
        "ollama": "pi-local-ollama",
    }.get(provider, "pi-local-lmstudio")
    return PiModelManager().resolve(endpoint_id=endpoint_id)


def _get_llm(endpoint: ResolvedPiEndpoint):
    """Build the browser-use LangChain LLM from a Pi-resolved endpoint."""
    return ChatOpenAI(  # pi-governed: endpoint identity from PiModelManager (W2, F-W2-1b)
        model=endpoint.model or "default",
        base_url=endpoint.base_url,
        api_key=endpoint.api_key,
        temperature=0.3,
    )


async def _record_browser_usage(
    *,
    endpoint: ResolvedPiEndpoint | None,
    project_id: str,
    agent_id: str,
    status: str,
    started: float,
    error_type: str | None = None,
) -> None:
    """One governed ledger row per browser run (``tool.browse_website``).

    The LangChain loop does not expose per-call token counts, so the row is a
    zeroed exact accounting carrying endpoint identity, latency, and outcome —
    never fabricated estimates. Ledger writes are never load-bearing.
    """
    from app.core.agentic.usage_ledger import record_agentic_usage

    await record_agentic_usage(
        engine="pi",
        purpose="tool.browse_website",
        project_id=project_id,
        agent_id=agent_id or "browser-use",
        outcome={
            "status": status,
            "endpoint_id": endpoint.endpoint_id if endpoint else "",
        },
        model=endpoint.model if endpoint else None,
        started_at=started,
        error_type=error_type,
    )


async def browse_website(
    url: str, task: str, max_steps: int = 10, *, project_id: str = "", agent_id: str = ""
) -> dict:
    """Browse a website and perform a task using an AI-driven browser agent.

    Args:
        url: Starting URL to navigate to
        task: What to do on the website (e.g., "Extract pricing information")
        max_steps: Maximum browser actions (default 10)

    Returns:
        dict with: result, urls_visited, screenshots, errors
    """
    if not BROWSER_AVAILABLE:
        return {
            "error": (
                "browser-use not installed. Install: pip install browser-use langchain-openai"
            ),
            "result": None,
        }

    started = time.perf_counter()
    endpoint: ResolvedPiEndpoint | None = None
    try:
        endpoint = _resolve_browser_endpoint()
        llm = _get_llm(endpoint)
        browser = Browser(config=BrowserConfig(headless=True))

        full_task = f"Navigate to {url} and {task}"
        agent = BrowserAgent(
            task=full_task,
            llm=llm,
            browser=browser,
            max_actions_per_step=3,
        )

        history = await agent.run(max_steps=max_steps)

        result = {
            "result": history.final_result() if history.is_done() else None,
            "success": (
                history.is_successful() if hasattr(history, "is_successful") else history.is_done()
            ),
            "urls_visited": (history.urls() if hasattr(history, "urls") else []),
            "actions_taken": (history.action_names() if hasattr(history, "action_names") else []),
            "extracted_content": (
                history.extracted_content() if hasattr(history, "extracted_content") else []
            ),
            "errors": history.errors() if hasattr(history, "errors") else [],
        }

        await browser.close()
        await _record_browser_usage(
            endpoint=endpoint,
            project_id=project_id,
            agent_id=agent_id,
            status="success",
            started=started,
        )
        return result

    except Exception as e:
        logger.exception("Browser browsing failed")
        await _record_browser_usage(
            endpoint=endpoint,
            project_id=project_id,
            agent_id=agent_id,
            status="error",
            started=started,
            error_type=type(e).__name__,
        )
        return {"error": str(e), "result": None}
