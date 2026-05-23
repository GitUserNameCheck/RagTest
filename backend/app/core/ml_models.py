from typing import TypedDict
from magika import Magika
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

class MLModels(TypedDict):
    magika: Magika
    embedding_model: SentenceTransformer
    reranker_model: CrossEncoder

ml_models: MLModels = {}