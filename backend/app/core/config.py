from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    app_name: str = "ScalableFastAPIProject"
    frontend_origin: str = ""
    db_url: str = ""
    s3_bucket_name: str = ""
    s3_login: str = ""
    s3_password: str = ""
    s3_url: str = ""
    pager_url: str = ""
    embedding_model_path: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    embedding_text_size: int = 500
    embedding_text_overlap: int = 100
    open_ai_api_key: str = None
    open_ai_url: str = ""
    open_ai_model_name: str = ""

config = Config()