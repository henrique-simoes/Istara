"""Browser automation service — wraps browser-use for agent-driven web browsing.

Uses browser-use library with LM Studio/Ollama as the LLM provider.
Compatible with any OpenAI-compatible endpoint via langchain_openai.ChatOpenAI.

Install: pip install browser-use langchain-openai
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)

BROWSER_AVAILABLE = False
try:
    from browser_use import Agent as BrowserAgent, Browser, BrowserConfig
    from langchain_openai import ChatOpenAI
    BROWSER_AVAILABLE = True
except ImportError:
    logger.info(
        "browser-use not installed — browse_website tool unavailable. "
        "Install: pip install browser-use langchain-openai"
    )


def _get_llm():
    """Create an LLM client pointing to the user's LM Studio or Ollama."""
    if settings.llm_provider == "lmstudio":
        return ChatOpenAI(
            model=settings.lmstudio_model or "default",
            base_url=f"{settings.lmstudio_host}/v1",
            api_key="lm-studio",
            temperature=0.3,
        )
    elif settings.llm_provider == "ollama":
        return ChatOpenAI(
            model=settings.ollama_model or "qwen3:latest",
            base_url=f"{settings.ollama_host}/v1",
            api_key="ollama",
            temperature=0.3,
        )
    else:
        return ChatOpenAI(
            model="default",
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            temperature=0.3,
        )


async def browse_website(url: str, task: str, max_steps: int = 10) -> dict:
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
                "browser-use not installed. "
                "Install: pip install browser-use langchain-openai"
            ),
            "result": None,
        }

    try:
        llm = _get_llm()
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
                history.is_successful()
                if hasattr(history, "is_successful")
                else history.is_done()
            ),
            "urls_visited": (
                history.urls() if hasattr(history, "urls") else []
            ),
            "actions_taken": (
                history.action_names() if hasattr(history, "action_names") else []
            ),
            "extracted_content": (
                history.extracted_content()
                if hasattr(history, "extracted_content")
                else []
            ),
            "errors": history.errors() if hasattr(history, "errors") else [],
        }

        await browser.close()
        return result

    except Exception as e:
        logger.exception("Browser browsing failed")
        return {"error": str(e), "result": None}
