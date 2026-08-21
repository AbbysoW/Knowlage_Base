

from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from kb_schemas import LogConfig






class EmbeddingModelConfig(BaseModel):
    name: str = "paraphrase-multilingual-MiniLM-L12-v2"


class DBConfig(BaseModel):
    name: str
    host: str = "localhost"
    port: int = 5432

    @computed_field
    @property
    def full_url(self) -> str:
        return f"{self.host}:{self.port}"




class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False
    telegram_api_token: str
    deepseek_api_key: str

    log: LogConfig = LogConfig()

    embedding_model: EmbeddingModelConfig = EmbeddingModelConfig()
    db: DBConfig = DBConfig()
settings = Settings()