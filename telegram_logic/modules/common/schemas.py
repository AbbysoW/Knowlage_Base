from pydantic import BaseModel
from datetime import datetime


class TranscriptionResult(BaseModel):
    text: str
    source_type: str          # "voice" | "pdf" | "image" | "video" | "link" | "text"
    source_ref: str | None    # URL или content-hash из attachment_store
    duration_sec: float | None = None
    confidence: float | None = None


# Post LLM Data
class Entity(BaseModel):
    name: str
    type: str                 # "person" | "concept" | "tool" | ...

class Fact(BaseModel):
    content: str               # verbatim: число, формула, дата, код — без искажений
    context: str | None = None

class Relation(BaseModel):
    target_note_id: str
    relation_type: str         # "extends" | "contradicts" | "example_of" | ...
    confidence: float

class FurtherReadingItem(BaseModel):
    title: str
    kind: str                  # "article" | "book" | "video"
    url: str | None = None

class Chunk(BaseModel):
    content: str
    embedding: list[float] | None = None

# Post LLM Data - Summary
class Note(BaseModel):
    title: str
    summary: str
    tags: list[str]
    entities: list[Entity]
    facts: list[Fact]
    relations: list[Relation]
    further_reading: list[FurtherReadingItem]
    created_at: datetime
    primary_category: str | None = None
    confidence: float | None = None


# DB Data
class DBPayload(BaseModel):
    note_id: str
    chunks: list[Chunk]        # каждый чанк со своим эмбеддингом (п. 2.5)
    metadata: dict             # зеркало frontmatter для SQL-индекса (п. 2.7)