import re

from pydantic import BaseModel, model_validator
from datetime import datetime

from typing import Any, Callable, Awaitable
from pathlib import Path


class LogConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"


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
    target_note_path: str
    relation_type: str         # "extends" | "contradicts" | "example_of" | ...
    confidence: float

class FurtherReadingItem(BaseModel):
    title: str
    kind: str                  # "article" | "book" | "video"
    url: str | None = None

# Designer
class Formatter(BaseModel):
    title: str
    tags: list[str]
    entities: list[Entity]
    facts: list[Fact]
    relations: list[Relation]
    created_at: datetime
    source_type: str
    file_name: str
    primary_category: str | None = None

    @model_validator(mode="after")
    def normalize_file_name(self):
        stem = self.file_name[:-3] if self.file_name.lower().endswith(".md") else self.file_name
        slug = re.sub(r"\s+", "_", stem.strip())
        self.file_name = f"{slug}.md"
        return self

    def tags_to_str(self):
        return '\n' + '\n'.join([f"- {tag}" for tag in self.tags])

    def entities_to_str(self):
        return '\n' + '\n'.join([f"- {entity.name}" for entity in self.entities])

    def relations_to_str(self):
        return '\n' + '\n'.join([f"- {relation.target_note_path}" for relation in self.relations])

class NoteDesigner(BaseModel):
    formatter: Formatter
    content:str


# Post LLM Data - Summary
class Note(BaseModel):
    title: str
    summary: str # Summary.content
    tags: list[str]
    entities: list[Entity]
    facts: list[Fact]
    relations: list[Relation]
    further_reading: list[FurtherReadingItem]
    created_at: datetime
    file_name: Path
    primary_category: Path | None = None


# DB Data

class Chunk(BaseModel):
    content: str
    embedding: list[float] | None = None

class DBPayload(BaseModel):
    chunks: list[Chunk]
    metadata: Formatter
    md: str
    raw_data: TranscriptionResult

class Step(BaseModel):
    name: str
    do: Callable[[], Awaitable[Any]]
    compensate: Callable[[], Awaitable[None]]
    result: Any = None
    done: bool = False