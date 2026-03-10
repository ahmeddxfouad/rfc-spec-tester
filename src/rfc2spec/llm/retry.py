from __future__ import annotations
from typing import Type, TypeVar
import time

from pydantic import BaseModel

from rfc2spec.llm.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


def complete_json_with_retries(
    provider: LLMProvider,
    prompt: str,
    schema: Type[T],
    *,
    max_attempts: int = 3,
    backoff_s: float = 0.25,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return provider.complete_json(prompt, schema)
        except Exception as err:  # provider errors, schema validation errors, transport errors
            last_err = err
            if attempt < max_attempts:
                time.sleep(backoff_s * attempt)
                continue
            raise RuntimeError(
                f"LLM JSON completion failed after {max_attempts} attempts for schema '{schema.__name__}'"
            ) from last_err

    # Unreachable, but keeps type checkers satisfied.
    raise RuntimeError("unreachable")
