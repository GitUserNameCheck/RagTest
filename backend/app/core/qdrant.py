from typing import Annotated
from fastapi import Depends
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.core.config import config

async def get_qdrant_client():
    qdrant_client = AsyncQdrantClient(
        url=config.qdrant_url, 
        api_key=config.qdrant_api_key
    )
    try:
        yield qdrant_client
    finally:
        await qdrant_client.close()

QdrantClient = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]

collection_name = "DocumentEmbedding"

async def init_qdrant(qdrant_client: AsyncQdrantClient):
    if not await qdrant_client.collection_exists(collection_name=collection_name):
        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=512,
                distance=models.Distance.COSINE
            ),
            hnsw_config=models.HnswConfigDiff(
                payload_m=16,
                m=0,
            ),
        )

        await qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="label",
            field_schema=models.PayloadSchemaType.KEYWORD
        )

        await qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.INTEGER
        )

        await qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="report_id",
            field_schema=models.PayloadSchemaType.INTEGER
        )

