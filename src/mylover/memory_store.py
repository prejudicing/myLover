from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from .config import settings
from .schemas import MemoryChunk


class MemoryStore:
    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(model=settings.embedding_model)
        self.vectorstore = Chroma(
            collection_name="mylover_memories",
            persist_directory=settings.chroma_dir,
            embedding_function=self.embeddings,
        )

    def add_memories(self, memories: list[MemoryChunk]) -> None:
        documents = [
            Document(
                page_content=memory.content,
                metadata={
                    "memory_id": memory.memory_id,
                    "source": memory.source,
                    "timestamp": memory.timestamp,
                    "memory_type": memory.memory_type,
                    "speaker": memory.speaker,
                },
            )
            for memory in memories
        ]
        if documents:
            self.vectorstore.add_documents(
                documents=documents,
                ids=[memory.memory_id for memory in memories],
            )

    def retrieve(
        self,
        query: str,
        k: int | None = None,
        *,
        speaker: str | None = None,
    ) -> list[MemoryChunk]:
        search_kwargs = {}
        if speaker:
            search_kwargs["filter"] = {"speaker": speaker}
        docs = self.vectorstore.similarity_search(query, k=k or settings.top_k, **search_kwargs)
        results: list[MemoryChunk] = []
        for index, doc in enumerate(docs):
            results.append(
                MemoryChunk(
                    memory_id=str(doc.metadata.get("memory_id", f"memory-{index}")),
                    content=doc.page_content,
                    source=str(doc.metadata.get("source", "unknown")),
                    timestamp=doc.metadata.get("timestamp"),
                    memory_type=doc.metadata.get("memory_type", "fact"),
                    speaker=doc.metadata.get("speaker", "lover"),
                )
            )
        return results

    def reset(self) -> None:
        self.vectorstore.reset_collection()

    def count(self) -> int:
        return self.vectorstore._collection.count()

    def add_dialogue_turn(
        self,
        *,
        session_id: str,
        content: str,
    ) -> MemoryChunk:
        timestamp = datetime.now().isoformat(timespec="seconds")
        memory = MemoryChunk(
            memory_id=f"turn-{session_id}-{uuid4().hex}",
            content=content,
            source=f"session:{session_id}",
            timestamp=timestamp,
            memory_type="episode",
            speaker="system",
        )
        self.add_memories([memory])
        return memory
