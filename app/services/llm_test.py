import asyncio

from app.models.provider_schema import LLMProvider
from app.infrastructure.llm.llm_client_factory import LLMClientFactory, llm_client_factory



async def main():
    # Get the Ollama client (default or explicitly)
    llm_client = llm_client_factory.of(LLMProvider.hg_local)

    # Call `generate` (you can also call `chat`)
    prompt = "Below is a table of scheduled activities. Extract each row into JSON with fields: activity, day, time, location"
    model = "meta-llama/Meta-Llama-3-8B-Instruct"

    result = await llm_client.generate(
        operation="test request",
        model=model,
        prompt=prompt
    )

    print(" generated result:\n", result)


if __name__ == '__main__':
    asyncio.run(main())