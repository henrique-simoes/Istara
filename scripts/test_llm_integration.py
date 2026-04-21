
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMStressTest")

async def test_llm_connectivity():
    """Test connection to the configured LLM provider."""
    # This is a simplified check that mimics how the orchestrator would check health
    from app.config import settings
    
    host = settings.ollama_host # or lmstudio_host, depending on provider
    logger.info(f"Testing connectivity to LLM provider at {host}...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Try to hit the health/tags endpoint
            resp = await client.get(f"{host}/api/tags") 
            if resp.status_code == 200:
                logger.info("✅ Connection successful.")
            else:
                logger.error(f"❌ Connection failed with status {resp.status_code}")
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")

if __name__ == "__main__":
    # Note: Requires Istara backend environment to be set up.
    # This script is designed to be run from the root directory.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "backend"))
    
    asyncio.run(test_llm_connectivity())
