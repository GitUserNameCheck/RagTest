from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from magika import Magika
from qdrant_client import AsyncQdrantClient
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
from torch import cuda

from app.api import document_api
from app.core.config import config
from app.core.logging import setup_logging
from app.core.qdrant import init_qdrant
from app.db.schema import Base, engine
from app.core.ml_models import ml_models

#https://github.com/Kludex/fastapi-tips/tree/main
# Should rewrite model management later like here https://starlette.dev/lifespan/
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logging.exception(f"Error when creating db models \n {e}")

    try:
        qdrant_client = AsyncQdrantClient(
            url=config.qdrant_url, 
            api_key=config.qdrant_api_key
        )
        await init_qdrant(qdrant_client)
        await qdrant_client.close()
    except Exception as e:
        logging.exception(f"Error when creating qdrant collection \n {e}")
    

    ml_models["magika"] = Magika()
    ml_models["embedding_model"] = SentenceTransformer(config.embedding_model_path)
    # ml_models["qwen_model"] = AutoModelForCausalLM.from_pretrained(
    #     config.qwen_path,
    #     torch_dtype="auto",
    #     device_map="auto"
    # )
    # logging.info(ml_models["qwen_model"].hf_device_map)
    # ml_models["qwen_tokenizer"] = AutoTokenizer.from_pretrained(config.qwen_path)


    if cuda.is_available():
        ml_models["embedding_model"] = ml_models["embedding_model"].to('cuda')

    yield
    ml_models.clear()

app = FastAPI(title=config.app_name, lifespan=lifespan)

origins = [
    config.frontend_origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(document_api.router, prefix="/api", tags=["document"])