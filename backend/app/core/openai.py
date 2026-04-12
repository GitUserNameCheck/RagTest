from typing import Annotated
from fastapi import Depends
from openai import AsyncOpenAI

from app.core.config import config

async def get_qdrant_client():
    client = AsyncOpenAI(
        api_key=config.open_ai_api_key,
        base_url=config.open_ai_url,
        max_retries=1,
    )
    try:
        yield client
    finally:
        await client.close()

OpenAIClient = Annotated[AsyncOpenAI, Depends(get_qdrant_client)]