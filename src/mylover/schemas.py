from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RelationshipState(BaseModel):
    session_id: str
    relationship_temperature: float = 0.0
    user_intimacy_pressure: float = 0.0
    avoidance_triggered: bool = False
    recent_shared_trivia: list[str] = Field(default_factory=list)
    recent_memory_keys: list[str] = Field(default_factory=list)
    conversation_history: list[str] = Field(default_factory=list)
    last_user_message: str = ""
    last_agent_reply: str = ""


class MemoryChunk(BaseModel):
    memory_id: str
    content: str
    source: str
    timestamp: str | None = None
    memory_type: Literal["fact", "habit", "style", "episode", "trigger", "inside_joke"] = "fact"
    speaker: Literal["self", "lover", "system"] = "lover"


class UserSignal(BaseModel):
    intimacy_pressure: float = Field(ge=0.0, le=1.0)
    user_distance: Literal["clingy", "neutral", "busy"]
    asks_for_emotional_reassurance: bool = False
    asks_for_practical_help: bool = False


class PipelineDebug(BaseModel):
    user_signal: UserSignal
    retrieved_memories: list[MemoryChunk] = Field(default_factory=list)
    prompt_preview: str = ""
    memory_written: bool = False
    memory_reason: str = ""
