from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
import time
import httpx
from loguru import logger


class BaseLLMClient(ABC):

    async def _measure_request(self, operation: str, model: str, func, **kwargs):
        start_time = time.time()
        try:
            logger.info(f"[{operation.upper()}] LLM request to {model} started")

            result = await func(model=model, **kwargs)

            logger.info(f"[{operation.upper()}] Success in {(time.time() - start_time):.2f}s")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"[{operation.upper()}] HTTP error {e.response.status_code} - {str(e)}")
            raise Exception(f"API error: {str(e)}")

        except httpx.RequestError as e:
            logger.error(f"[{operation.upper()}] Request error: {str(e)}")
            raise Exception(f"API request error: {str(e)}")

        except Exception as e:
            logger.exception(f"[{operation.upper()}] Unexpected error: {str(e)}")
            raise Exception(f"API unexpected error: {str(e)}")


    @abstractmethod
    async def generate(self, operation: str, model: str, prompt: str, image: Optional[str] = None)->str:
        pass


    @abstractmethod
    async def chat(self, operation: str, model: str, prompt: str, history: Optional[list] = None, image: Optional[str] = None):
        pass