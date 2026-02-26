"""Factory for constructing provider-specific LLM clients."""

from __future__ import annotations

import os
from typing import Optional

from .azure_openai_client import AzureOpenAIClient
from .base import LLMClient, LLMClientError
from .gemini_client import GeminiClient


def create_llm_client(
    *,
    provider: str,
    model: Optional[str],
    timeout_seconds: int,
) -> LLMClient:
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise LLMClientError(
                "Gemini requires GEMINI_API_KEY or GOOGLE_API_KEY in environment."
            )
        resolved_model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
        return GeminiClient(api_key=api_key, model=resolved_model, timeout_seconds=timeout_seconds)

    if provider == "azure_openai":
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
        if not deployment:
            deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "").strip()
        if not endpoint or not api_key or not deployment:
            raise LLMClientError(
                "Azure OpenAI requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, "
                "and AZURE_OPENAI_DEPLOYMENT (or AZURE_OPENAI_DEPLOYMENT_NAME) in environment."
            )
        resolved_model = model or os.environ.get("AZURE_OPENAI_MODEL") or "gpt-5.2"
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        return AzureOpenAIClient(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            model=resolved_model,
            api_version=api_version,
            timeout_seconds=timeout_seconds,
        )

    raise LLMClientError(f"Unsupported LLM provider: {provider}")
