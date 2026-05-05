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
        LIVE_LLM_PROFILES,
        get_profile_api_key,
    )

    failures = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for profile in LIVE_LLM_PROFILES:
            api_key = get_profile_api_key(profile)
            if not api_key:
                message = (
                    f"Missing {profile.name} test API key. Set one of "
                    f"{', '.join(profile.key_env_names)} or store it in the local keychain."
                )
                if profile.required:
                    logger.error(message)
                    failures += 1
                else:
                    logger.info("Skipping optional fallback profile: %s", profile.name)
                continue

            url = profile.endpoint("chat/completions")
            logger.info(
                "Testing %s chat completions at %s with model %s...",
                profile.name,
                url,
                profile.model,
            )
            try:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": profile.model,
                        "messages": [{"role": "user", "content": "Reply with ok."}],
                        "temperature": 0,
                        "max_tokens": 8,
                    },
                )
                if resp.status_code == 200:
                    logger.info("%s connection successful.", profile.name)
                else:
                    logger.error(
                        "%s connection failed with status %s",
                        profile.name,
                        resp.status_code,
                    )
                    failures += 1
            except Exception as exc:
                logger.error("%s connection error: %s", profile.name, exc)
                failures += 1

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    # Note: Requires Istara backend environment to be set up.
    # This script is designed to be run from the root directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

    asyncio.run(test_llm_connectivity())
