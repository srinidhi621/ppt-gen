"""Structured retry wrapper for V3 LLM calls.

Wraps any LLM client call with: call → parse → validate → retry-with-context.
Callers pass a validator function; the wrapper handles the retry loop.

Usage::

    from src.v3.llm_retry import retry_generate_json

    def my_validator(parsed: dict) -> list[str]:
        errors = []
        if "slides" not in parsed:
            errors.append("Missing 'slides' key")
        return errors  # empty = valid

    result = retry_generate_json(
        client, model="gpt-5.4",
        instructions="...", input_text="...",
        validator=my_validator, max_retries=2,
    )
"""

from __future__ import annotations

import logging
from typing import Callable

from src.v3.llm_client import (
    LLMBudgetExhausted,
    LLMInfraError,
    LLMResponse,
    LLMValidationError,
    ResponsesClient,
)

logger = logging.getLogger(__name__)

# Type alias for validator functions.
# A validator receives the parsed dict and returns a list of error strings.
# Empty list = valid.
Validator = Callable[[dict], list[str]]


def retry_generate_json(
    client: ResponsesClient,
    model: str,
    instructions: str,
    input_text: str,
    *,
    caller: str = "unknown",
    validator: Validator | None = None,
    max_retries: int = 2,
    temperature: float = 0.3,
    max_output_tokens: int = 4096,
) -> LLMResponse:
    """Call generate_json with structured retries.

    On validation failure, the error messages are folded into the next
    prompt so the LLM can self-correct.

    Args:
        client: The Responses API client.
        model: Model name (e.g. "gpt-5.4").
        instructions: System-level instructions.
        input_text: User-level input.
        validator: Optional function that checks the parsed dict.
            Returns a list of error strings (empty = valid).
        max_retries: Number of retries after the first attempt.
        temperature: LLM temperature.
        max_output_tokens: Max output tokens.

    Returns:
        LLMResponse with .parsed containing the validated dict.

    Raises:
        LLMInfraError: On infrastructure failure (no retry).
        LLMBudgetExhausted: When all retries fail.
    """
    total_usage_input = 0
    total_usage_output = 0
    last_error = ""
    current_input = input_text

    for attempt in range(1 + max_retries):
        try:
            result = client.generate_json(
                model,
                instructions,
                current_input,
                caller=caller,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except LLMInfraError:
            raise  # No retry on infra errors
        except LLMValidationError as exc:
            # JSON parse failure from the client — retryable
            last_error = str(exc)
            logger.warning(
                "Attempt %d/%d: LLM response failed parsing: %s",
                attempt + 1, 1 + max_retries, last_error,
            )
            current_input = _build_retry_input(input_text, last_error)
            total_usage_input += 0  # No usage on parse failure
            continue

        # Track usage
        total_usage_input += result.usage.input_tokens
        total_usage_output += result.usage.output_tokens

        # Run validator if provided
        if validator is not None:
            errors = validator(result.parsed)
            if errors:
                last_error = "; ".join(errors)
                logger.warning(
                    "Attempt %d/%d: Validation failed: %s",
                    attempt + 1, 1 + max_retries, last_error,
                )
                current_input = _build_retry_input(input_text, last_error)
                continue

        # Success
        logger.info(
            "LLM call succeeded on attempt %d/%d (%d in, %d out tokens)",
            attempt + 1, 1 + max_retries,
            total_usage_input, total_usage_output,
        )
        return result

    # All retries exhausted
    raise LLMBudgetExhausted(
        f"Failed after {1 + max_retries} attempts. Last error: {last_error}"
    )


def retry_generate_json_with_images(
    client: ResponsesClient,
    model: str,
    instructions: str,
    input_text: str,
    images: list,
    *,
    caller: str = "unknown",
    validator: Validator | None = None,
    max_retries: int = 1,
    temperature: float = 0.3,
    max_output_tokens: int = 4096,
) -> LLMResponse:
    """Call generate_json_with_images with structured retries.

    Same semantics as retry_generate_json but passes images through.
    """
    last_error = ""
    current_input = input_text

    for attempt in range(1 + max_retries):
        try:
            result = client.generate_json_with_images(
                model,
                instructions,
                current_input,
                images,
                caller=caller,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except LLMInfraError:
            raise
        except LLMValidationError as exc:
            last_error = str(exc)
            logger.warning(
                "Attempt %d/%d: LLM response failed parsing: %s",
                attempt + 1, 1 + max_retries, last_error,
            )
            current_input = _build_retry_input(input_text, last_error)
            continue

        if validator is not None:
            errors = validator(result.parsed)
            if errors:
                last_error = "; ".join(errors)
                logger.warning(
                    "Attempt %d/%d: Validation failed: %s",
                    attempt + 1, 1 + max_retries, last_error,
                )
                current_input = _build_retry_input(input_text, last_error)
                continue

        return result

    raise LLMBudgetExhausted(
        f"Failed after {1 + max_retries} attempts. Last error: {last_error}"
    )


def _build_retry_input(original_input: str, error_message: str) -> str:
    """Build a retry prompt that includes the original input and the error context."""
    return (
        f"{original_input}\n\n"
        f"---\n"
        f"YOUR PREVIOUS RESPONSE FAILED VALIDATION. Fix the following errors "
        f"and return a corrected response:\n\n"
        f"{error_message}"
    )
