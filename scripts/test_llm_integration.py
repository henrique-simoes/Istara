import asyncio
import httpx
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMStressTest")


async def test_llm_connectivity():
    """Test the live LLM endpoints used by Istara's real LLM tests."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.llm_test_config import (
        PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
        post_live_llm_chat_completion,
    )

    failures = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        logger.info(
            "Testing Gemini-first live LLM contract: %s primary attempts before fallback.",
            PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
        )
        try:
            result = await post_live_llm_chat_completion(client)
            logger.info(
                "%s connection successful at %s with model %s%s.",
                result.profile_name,
                result.endpoint,
                result.model,
                " after Gemini fallback" if result.fallback_used else "",
            )
        except Exception as exc:
            logger.error("Live LLM connectivity failed: %s", exc)
            failures += 1

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    # Note: Requires Istara backend environment to be set up.
    # This script is designed to be run from the root directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

    asyncio.run(test_llm_connectivity())
