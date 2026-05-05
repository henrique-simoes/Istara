import asyncio
import httpx
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMStressTest")


async def test_llm_connectivity():
    """Test the live LLM endpoint used by Istara's real LLM tests."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.llm_test_config import (
        GEMINI_OPENAI_BASE_URL,
        GEMINI_TEST_MODEL,
        get_live_llm_api_key,
    )

    api_key = get_live_llm_api_key()
    if not api_key:
        logger.error(
            "Missing Gemini test API key. Set ISTARA_LLM_TEST_API_KEY, GEMINI_API_KEY, "
            "or store it in the local keychain."
        )
        return

    logger.info(
        "Testing Gemini OpenAI-compatible chat completions at %s with model %s...",
        GEMINI_OPENAI_BASE_URL,
        GEMINI_TEST_MODEL,
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{GEMINI_OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": GEMINI_TEST_MODEL,
                    "messages": [{"role": "user", "content": "Reply with ok."}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
            )
            if resp.status_code == 200:
                logger.info("Connection successful.")
            else:
                logger.error(f"❌ Connection failed with status {resp.status_code}")
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")


if __name__ == "__main__":
    # Note: Requires Istara backend environment to be set up.
    # This script is designed to be run from the root directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

    asyncio.run(test_llm_connectivity())
