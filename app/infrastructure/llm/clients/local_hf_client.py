from typing import Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login
from loguru import logger

from app.infrastructure.llm.clients.base_llm_client import BaseLLMClient
from app.core.settings import get_settings


class LocalHFClient(BaseLLMClient):
    def __init__(self):
        super().__init__()

        # Login to Hugging Face Hub before loading models/tokenizers
        hf_token = get_settings().HG_API_KEY
        login(token=hf_token)


    def _generate_text(self, prompt: str, model: str, max_new_tokens: int = 500, temperature: float = 0.7) -> str:
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForCausalLM.from_pretrained(model)
        self.model.eval()

        # Move to GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        # Assign pad_token if missing
        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

        prompt_formatted = self.tokenizer.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True)

        inputs = self.tokenizer(prompt_formatted, return_tensors="pt", padding=True, truncation=True)
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)

        eos_token_id = self.tokenizer.eos_token_id or self.tokenizer.pad_token_id or 0
        pad_token_id = self.tokenizer.pad_token_id or eos_token_id or 0

        logger.debug(f" Start LLM generation for  {input_ids.shape[1]} input tokens...wait...")
        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                #max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=pad_token_id,
                eos_token_id=eos_token_id,
            )

        output_ids_stripped = output_ids[0][input_ids.shape[-1]:]       # remove input from context
        generated_text = self.tokenizer.decode(output_ids_stripped, skip_special_tokens=True)
        return generated_text

    async def _make_generate_request(self, prompt: str, model: str) -> str:
        return self._generate_text(prompt, model)

    async def _make_chat_request(self, prompt: str, model: str, history: Optional[list] = None) -> str:
        # Naive chat emulation
        chat_prompt = ""
        for msg in history or []:
            chat_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
        chat_prompt += f"User: {prompt}\nAssistant:"

        return self._generate_text(chat_prompt)

    async def generate(self, operation: str, model: str, prompt: str, image: Optional[str] = None):
        return await self._measure_request(
            operation=operation,
            model=model,
            func=self._make_generate_request,
            prompt=prompt,
        )

    async def chat(self, operation: str, model: str, prompt: str, history: Optional[list] = None, image: Optional[str] = None):
        return await self._measure_request(
            operation=operation,
            model=model,
            func=self._make_chat_request,
            prompt=prompt,
            history=history,
        )
