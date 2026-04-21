from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


@dataclass(slots=True)
class Settings:
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    chroma_dir: str = os.getenv("MYLOVER_CHROMA_DIR", ".chroma")
    top_k: int = int(os.getenv("MYLOVER_TOP_K", "6"))
    memory_write_threshold: float = float(os.getenv("MYLOVER_MEMORY_WRITE_THRESHOLD", "0.65"))


settings = Settings()
