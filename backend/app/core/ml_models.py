from typing import TypedDict
from magika import Magika
from sentence_transformers import SentenceTransformer
from transformers import PreTrainedModel, PreTrainedTokenizerBase, Qwen2ForCausalLM


class MLModels(TypedDict):
    magika: Magika
    embedding_model: SentenceTransformer
    # qwen_model: Qwen2ForCausalLM
    # qwen_tokenizer: PreTrainedTokenizerBase

ml_models: MLModels = {}