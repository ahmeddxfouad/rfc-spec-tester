from __future__ import annotations
from typing import Type, TypeVar, Protocol, Any, Dict
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):
    name: str
    def complete_json(self, prompt: str, schema: Type[T]) -> T: ...

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"Unknown provider '{name}'. Available: {sorted(self._providers)}")
        return self._providers[name]
