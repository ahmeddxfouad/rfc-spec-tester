from __future__ import annotations
from rfc2spec.llm.base import ProviderRegistry
from rfc2spec.llm.providers.mock import MockLLM

def default_registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(MockLLM())
    return reg
