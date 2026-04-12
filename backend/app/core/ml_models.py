from typing import TypedDict
from magika import Magika
from sentence_transformers import SentenceTransformer

class MLModels(TypedDict):
    magika: Magika
    embedding_model: SentenceTransformer

ml_models: MLModels = {}