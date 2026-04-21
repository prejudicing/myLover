from __future__ import annotations

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
                },
            )
            for memory in memories
        ]
        if documents:
            self.vectorstore.add_documents(
                documents=documents,
                ids=[memory.memory_id for memory in memories],
            )

    def retrieve(self, query: str, k: int | None = None) -> list[MemoryChunk]:
        docs = self.vectorstore.similarity_search(query, k=k or settings.top_k)
        results: list[MemoryChunk] = []
        for index, doc in enumerate(docs):
            results.append(
                MemoryChunk(
                    memory_id=str(doc.metadata.get("memory_id", f"memory-{index}")),
                    content=doc.page_content,
                    source=str(doc.metadata.get("source", "unknown")),
                    timestamp=doc.metadata.get("timestamp"),
                    memory_type=doc.metadata.get("memory_type", "fact"),
                )
            )
        return results

    def reset(self) -> None:
        self.vectorstore.reset_collection()

    def count(self) -> int:
        return self.vectorstore._collection.count()
