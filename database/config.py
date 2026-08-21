

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from kb_schemas import LogConfig

from pathlib import Path

class Transaction(BaseModel):
    wal_dir: Path = Path("/var/data/wal")

class FileStore(BaseModel):
    name: str = 'file_store'
    path: Path = Path("/data/files")

class MetadataStore(BaseModel):
    name: str = 'metadata_store'
    path: Path = Path("/data/metadata")

class VectorStore(BaseModel):
    name: str = 'vector_store'
    path: Path = Path("/data/vectors")

class DB(BaseModel):
    file_store: FileStore = FileStore()
    metadata_store: MetadataStore = MetadataStore()
    vector_store: VectorStore = VectorStore()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False
    tx: Transaction = Transaction()

    log: LogConfig = LogConfig()
    db: DB = DB()
settings = Settings()
