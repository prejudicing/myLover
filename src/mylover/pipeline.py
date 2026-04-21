from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import settings
from .memory_store import MemoryStore
from .prompts import build_reply_context, build_system_prompt
from .schemas import PipelineDebug, RelationshipState, UserSignal

MEMORY_KEYWORDS = (
    "宿舍",
    "学校",
    "信号",
    "药",
    "吃饭",
    "下雨",
    "考试",
    "发烧",
    "门禁",
    "上课",
    "走廊",
    "高铁",
    "医院",
    "到家",
)


def classify_user_signal(user_message: str) -> UserSignal:
    lowered = user_message.lower()
    asks_for_emotional_reassurance = any(
        phrase in user_message
        for phrase in [
            "爱不爱我",
            "想我吗",
            "你是不是不在乎",
            "你都不理我",
            "不在乎我",
            "根本不在乎我",
            "没怎么理我",
            "为什么不理我",
            "是不是烦我",
            "是不是不想理我",
        ]
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

    next_state.conversation_history = [*next_state.conversation_history, f"user: {user_message}"]

    return next_state


def _normalize_memory_key(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def build_memory_candidate(
    *,
    state: RelationshipState,
    signal: UserSignal,
    user_message: str,
    reply: str,
    retrieved_memories: list,
) -> tuple[str | None, str, str]:
    user_clean = user_message.strip()
    reply_clean = reply.strip()
    if len(user_clean) < 5:
        return None, "", "too_short"

    user_key = _normalize_memory_key(user_clean)
    if user_key in state.recent_memory_keys:
        return None, "", "recent_duplicate"

    if any(memory.content.strip() == user_clean for memory in retrieved_memories):
        return None, "", "already_in_store"

    has_fact_signal = any(keyword in f"{user_clean} {reply_clean}" for keyword in MEMORY_KEYWORDS)
    has_relationship_signal = signal.asks_for_emotional_reassurance or signal.asks_for_practical_help
    has_busy_signal = signal.user_distance == "busy"

    if not any([has_fact_signal, has_relationship_signal, has_busy_signal]):
        return None, "", "not_salient"

    if has_relationship_signal:
        content = f"关系片段：用户表达了情绪压力“{user_clean}”\n她当时的回应是：{reply_clean}"
        reason = "relationship_signal"
    elif has_fact_signal:
        content = f"共同记忆：{user_clean}\n当时她回：{reply_clean}"
        reason = "salient_fact"
    else:
        content = f"生活报备：{user_clean}\n她接着说：{reply_clean}"
        reason = "busy_or_routine"

    return content, user_key, reason


def shape_reply(user_message: str, reply: str, signal: UserSignal) -> str:
    text = " ".join(reply.strip().split())
    if not text:
        return text

    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]
    if not sentences:
        return text

    max_sentences = 2
    if signal.asks_for_emotional_reassurance or any(
        phrase in user_message for phrase in ["不是她", "不会回复这么多", "你不是她"]
    ):
        max_sentences = 1

    trimmed_sentences = sentences[:max_sentences]
    allow_question = signal.asks_for_practical_help and not signal.asks_for_emotional_reassurance
    if not allow_question:
        non_question_sentences = [
            sentence for sentence in trimmed_sentences if "？" not in sentence and "?" not in sentence
        ]
        if non_question_sentences:
            trimmed_sentences = non_question_sentences
        else:
            trimmed_sentences = [
                re.sub(r"[？?].*$", "", trimmed_sentences[0]).strip("，,、 ")
            ]

    trimmed = "".join(sentence for sentence in trimmed_sentences if sentence).strip()

    if not trimmed:
        trimmed = "好呢。"

    if len(trimmed) > 90:
        trimmed = trimmed[:90].rstrip("，,、 ") + "。"

    if trimmed[-1] not in "。！？!?~…":
        trimmed += "。"

    return trimmed


class MyLoverPipeline:
    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        self.memory_store = memory_store or MemoryStore()
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.75)
        self.session_dir = Path(settings.session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self, session_id: str) -> RelationshipState:
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            return RelationshipState(session_id=session_id)
        return RelationshipState.model_validate_json(path.read_text(encoding="utf-8"))

    def save_state(self, state: RelationshipState) -> None:
        path = self.session_dir / f"{state.session_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def list_sessions(self) -> list[str]:
        sessions = [path.stem for path in sorted(self.session_dir.glob("*.json"))]
        return sessions or ["default"]

    def invoke(
        self,
        state: RelationshipState,
        user_message: str,
    ) -> tuple[str, RelationshipState, PipelineDebug]:
        signal = classify_user_signal(user_message)
        next_state = update_state_before_generation(state, signal, user_message)
        memories = self.memory_store.retrieve(user_message, speaker="lover")

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
        raw_reply = response.content if isinstance(response.content, str) else str(response.content)
        reply = shape_reply(user_message, raw_reply, signal)
        next_state.last_agent_reply = reply
        next_state.conversation_history = [*next_state.conversation_history, f"lover: {reply}"]

        if any(keyword in f"{user_message} {reply}" for keyword in MEMORY_KEYWORDS):
            recent = next_state.recent_shared_trivia[-4:]
            next_state.recent_shared_trivia = [*recent, user_message[:30]]

        candidate_content, memory_key, memory_reason = build_memory_candidate(
            state=state,
            signal=signal,
            user_message=user_message,
            reply=reply,
            retrieved_memories=memories,
        )
        debug = PipelineDebug(
            user_signal=signal,
            retrieved_memories=memories,
            prompt_preview=prompt,
            memory_written=False,
            memory_reason=memory_reason,
        )
        if candidate_content and memory_key:
            self.memory_store.add_dialogue_turn(
                session_id=state.session_id,
                content=candidate_content,
            )
            next_state.recent_memory_keys = [*next_state.recent_memory_keys[-14:], memory_key]
            debug.memory_written = True

        return reply, next_state, debug

    def chat(self, session_id: str, user_message: str) -> tuple[str, RelationshipState, PipelineDebug]:
        state = self.load_state(session_id)
        reply, next_state, debug = self.invoke(state, user_message)
        self.save_state(next_state)
        return reply, next_state, debug

    @staticmethod
    def iter_messages(state: RelationshipState) -> Iterable[tuple[str, str]]:
        for item in state.conversation_history:
            if item.startswith("user: "):
                yield ("user", item.removeprefix("user: "))
            elif item.startswith("lover: "):
                yield ("assistant", item.removeprefix("lover: "))
