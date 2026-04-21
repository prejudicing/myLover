from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RelationshipState(BaseModel):
    session_id: str
    relationship_temperature: float = 0.0
    user_intimacy_pressure: float = 0.0
    avoidance_triggered: bool = False
    recent_shared_trivia: list[str] = Field(default_factory=list)
    last_user_message: str = ""
    last_agent_reply: str = ""


class MemoryChunk(BaseModel):
    memory_id: str
    content: str
    source: str
    timestamp: str | None = None
    memory_type: Literal["fact", "habit", "style", "episode", "trigger", "inside_joke"] = "fact"


class UserSignal(BaseModel):
    intimacy_pressure: float = Field(ge=0.0, le=1.0)
    user_distance: Literal["clingy", "neutral", "busy"]
    asks_for_emotional_reassurance: bool = False
    asks_for_practical_help: bool = False
