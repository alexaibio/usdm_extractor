from typing import Dict, Optional

from loguru import logger

from app.models.provider_schema import LLMProvider
from app.infrastructure.llm.clients.base_llm_client import BaseLLMClient
from app.infrastructure.llm.clients.deepseek_client import DeepSeekClient
from app.infrastructure.llm.clients.ollama_client import OllamaClient
from app.infrastructure.llm.clients.local_hf_client import LocalHFClient


class LLMClientFactory:
    def __init__(self):
        self._llm_providers: Dict[str, BaseLLMClient] = {}      # this is a singleton cache for providers
        self._default_llm_provider = LLMProvider.ollama


    def of(self, provider: Optional[LLMProvider] = None):
        current_provider = provider or self._default_llm_provider

        # Create provider instance if not already created
        if current_provider.value not in self._llm_providers:
            if current_provider == LLMProvider.deepseek:
                self._llm_providers[current_provider.value] = DeepSeekClient()
            elif current_provider == LLMProvider.ollama:
                self._llm_providers[current_provider.value] = OllamaClient()
            elif current_provider == LLMProvider.hg_local:
                self._llm_providers[current_provider.value] = LocalHFClient()
            else:
                logger.warning(f"Unknown provider: {current_provider}")
                raise

        return self._llm_providers[current_provider.value]

# instantiation here insures that we load it only once.
llm_client_factory = LLMClientFactory()