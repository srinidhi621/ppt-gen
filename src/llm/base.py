"""Provider-agnostic LLM client contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class LLMClientError(RuntimeError):
    """Raised on transport, authentication, or invalid provider responses."""


@dataclass
class LLMUsage:
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None
    raw_usage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "raw_usage": self.raw_usage,
        }


@dataclass
class LLMResponse:
    data: Dict[str, Any]
    usage: Optional[LLMUsage] = None


class LLMClient(Protocol):
    provider: str
    model: str

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate a JSON object from prompts."""

    def generate_json_with_images(
        self, system_prompt: str, user_prompt: str, image_paths: list[Path]
    ) -> LLMResponse:
        """Generate a JSON object from prompts and local image paths."""
