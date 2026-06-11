"""
LLM Factory - creates OpenAI, Ollama, or Gemini LLM based on configuration.
"""

import logging

logger = logging.getLogger(__name__)


def get_llm():
    """
    Get the configured LLM instance.

    Uses LLM_PROVIDER env/setting to determine provider:
    - 'openai' -> ChatOpenAI (requires OPENAI_API_KEY)
    - 'ollama' -> ChatOllama (requires OLLAMA_BASE_URL)
    - 'gemini' -> ChatGoogleGenerativeAI (requires GEMINI_API_KEY)
    """
    try:
        from django.conf import settings

        provider = settings.LLM_PROVIDER
        openai_key = settings.OPENAI_API_KEY
        openai_model = settings.OPENAI_MODEL
        ollama_url = settings.OLLAMA_BASE_URL
        ollama_model = settings.OLLAMA_MODEL
        gemini_key = settings.GEMINI_API_KEY
        gemini_model = settings.GEMINI_MODEL
    except Exception:
        import os

        provider = os.environ.get("LLM_PROVIDER", "openai")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    provider = (provider or "openai").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info("Using Ollama LLM: %s at %s", ollama_model, ollama_url)
        return ChatOllama(
            model=ollama_model,
            base_url=ollama_url,
            reasoning=False,
            temperature=0.7,
            num_predict=512,
            keep_alive="10m",
        )

    if provider == "gemini":
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.info("Using Gemini LLM: %s", gemini_model)
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=gemini_key,
            temperature=0.7,
            max_output_tokens=1024,
        )

    from langchain_openai import ChatOpenAI

    logger.info("Using OpenAI LLM: %s", openai_model)
    return ChatOpenAI(
        model=openai_model,
        api_key=openai_key,
        temperature=0.7,
        max_tokens=1024,
    )
