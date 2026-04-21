from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import settings
from .memory_store import MemoryStore
from .prompts import build_reply_context, build_system_prompt
from .schemas import RelationshipState, UserSignal


def classify_user_signal(user_message: str) -> UserSignal:
    lowered = user_message.lower()
    asks_for_emotional_reassurance = any(
        phrase in user_message for phrase in ["爱不爱我", "想我吗", "你是不是不在乎", "你都不理我"]
    )
    asks_for_practical_help = any(
        phrase in user_message for phrase in ["帮我", "怎么弄", "怎么办", "要不要"]
    )

    intimacy_pressure = 0.2
    if asks_for_emotional_reassurance:
        intimacy_pressure = 0.85
    elif len(user_message) > 40:
        intimacy_pressure = 0.55

    user_distance = "neutral"
    if any(phrase in lowered for phrase in ["先忙", "晚点聊", "在上班", "在忙"]):
        user_distance = "busy"
    elif intimacy_pressure > 0.7:
        user_distance = "clingy"

    return UserSignal(
        intimacy_pressure=intimacy_pressure,
        user_distance=user_distance,
        asks_for_emotional_reassurance=asks_for_emotional_reassurance,
        asks_for_practical_help=asks_for_practical_help,
    )


def update_state_before_generation(
    state: RelationshipState,
    signal: UserSignal,
    user_message: str,
) -> RelationshipState:
    next_state = state.model_copy(deep=True)
    next_state.last_user_message = user_message
    next_state.user_intimacy_pressure = signal.intimacy_pressure
    next_state.avoidance_triggered = signal.intimacy_pressure > 0.7

    if signal.user_distance == "busy":
        next_state.relationship_temperature += 0.05
    elif signal.user_distance == "clingy":
        next_state.relationship_temperature -= 0.03

    return next_state


def should_write_memory(user_message: str, reply: str) -> bool:
    combined = f"{user_message} {reply}"
    return any(keyword in combined for keyword in ["宿舍", "学校", "信号", "药", "吃饭", "下雨"])


class MyLoverPipeline:
    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        self.memory_store = memory_store or MemoryStore()
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.9)

    def invoke(self, state: RelationshipState, user_message: str) -> tuple[str, RelationshipState]:
        signal = classify_user_signal(user_message)
        next_state = update_state_before_generation(state, signal, user_message)
        memories = self.memory_store.retrieve(user_message)

        prompt = build_reply_context(
            state=next_state,
            signal=signal,
            memories=memories,
            user_message=user_message,
        )
        response = self.llm.invoke(
            [
                SystemMessage(content=build_system_prompt()),
                HumanMessage(content=prompt),
            ]
        )
        reply = response.content if isinstance(response.content, str) else str(response.content)
        next_state.last_agent_reply = reply

        if should_write_memory(user_message, reply):
            recent = next_state.recent_shared_trivia[-4:]
            next_state.recent_shared_trivia = [*recent, user_message[:30]]

        return reply, next_state
