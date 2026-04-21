from __future__ import annotations

import argparse
import json
from pathlib import Path

from .memory_store import MemoryStore
from .schemas import MemoryChunk

FACT_KEYWORDS = [
    "宿舍",
    "学校",
    "食堂",
    "停电",
    "信号",
    "药",
    "上课",
    "下雨",
    "高铁",
    "医院",
    "发烧",
    "头疼",
    "姨妈",
    "考试",
    "教室",
    "老师",
    "门禁",
    "走廊",
    "充电",
]

HABIT_KEYWORDS = [
    "吃饭",
    "睡觉",
    "起床",
    "吃药",
    "洗澡",
    "下班",
    "忙完",
    "到家",
    "睡醒",
]

STYLE_KEYWORDS = [
    "哈哈",
    "笑死",
    "好呢",
    "宝儿",
    "呦",
    "嗯嗯",
    "好的呀",
    "晚安",
]

INSIDE_JOKE_KEYWORDS = [
    "笨蛋",
    "傻",
    "猪",
    "离谱",
    "笑死我了",
]


def _normalize_content(content: str) -> str:
    return " ".join(content.split())


def _infer_memory_type(content: str) -> str | None:
    if any(keyword in content for keyword in FACT_KEYWORDS):
        return "fact"
    if any(keyword in content for keyword in HABIT_KEYWORDS):
        return "habit"
    if any(keyword in content for keyword in STYLE_KEYWORDS):
        return "style"
    if any(keyword in content for keyword in INSIDE_JOKE_KEYWORDS):
        return "inside_joke"
    return None


def _is_candidate_text(content: str) -> bool:
    if not content or len(content) > 40:
        return False
    if content in {"嗯", "哦", "好", "哈哈", "晚安"}:
        return False
    return _infer_memory_type(content) is not None


def extract_candidate_memories(chat_export_path: str | Path) -> list[MemoryChunk]:
    """
    Lightweight MVP extraction logic.

    The first pass keeps short factual, habit-like, or stylistic snippets that
    can be reused as shared memory. This is deliberately conservative to reduce
    false memories and duplicate trivial chatter.
    """

    path = Path(chat_export_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    messages = payload.get("messages", [])

    memories: list[MemoryChunk] = []
    seen: set[tuple[str, str]] = set()

    for message in messages:
        if message.get("type") != "文本消息":
            continue

        content = _normalize_content(str(message.get("content", "")).strip())
        if not _is_candidate_text(content):
            continue

        memory_type = _infer_memory_type(content) or "fact"
        signature = (memory_type, content)
        if signature in seen:
            continue
        seen.add(signature)

        memories.append(
            MemoryChunk(
                memory_id=str(message.get("platformMessageId", message.get("localId"))),
                content=content,
                source=path.name,
                timestamp=message.get("formattedTime"),
                memory_type=memory_type,
            )
        )

    return memories


def build_memory_store(chat_export_path: str | Path, *, reset: bool = False) -> list[MemoryChunk]:
    memories = extract_candidate_memories(chat_export_path)
    store = MemoryStore()
    if reset:
        store.reset()
    store.add_memories(memories)
    return memories


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma memories from WeFlow chat export")
    parser.add_argument(
        "--input",
        default="raw_data/json_data/texts/私聊_A是巧巧儿呢～.json",
        help="Path to chat export JSON",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the Chroma collection before ingesting",
    )
    args = parser.parse_args()

    memories = build_memory_store(args.input, reset=args.reset)
    store = MemoryStore()

    print(f"ingested_memories={len(memories)}")
    print(f"collection_count={store.count()}")
    print("sample_memories:")
    for memory in memories[:10]:
        print(f"- [{memory.memory_type}] {memory.content}")


if __name__ == "__main__":
    main()
