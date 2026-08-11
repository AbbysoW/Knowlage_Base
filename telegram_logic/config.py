

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict






class LogConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"


class EmbeddingModelConfig(BaseModel):
    name: str = "paraphrase-multilingual-MiniLM-L12-v2"


class DBConfig(BaseModel):
    name: str
    host: str = "localhost"
    port: int = 5432



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False

    log: LogConfig = LogConfig()

    embedding_model: EmbeddingModelConfig = EmbeddingModelConfig()
    db: DBConfig = DBConfig()
settings = Settings()