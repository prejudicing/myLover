from __future__ import annotations

import asyncio
import json
import random
import signal
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from wecom_aibot_sdk import WSClient

from .config import settings
from .pipeline import MyLoverPipeline


@dataclass(slots=True)
class WeComInboundMessage:
    chat_id: str
    user_id: str
    msg_id: str
    content: str
    chat_type: str


def _extract_text(frame: dict[str, Any]) -> WeComInboundMessage | None:
    body = frame.get("body", {})
    if body.get("msgtype") != "text":
        return None

    text = ((body.get("text") or {}).get("content") or "").strip()
    if not text:
        return None

    user_id = ((body.get("from") or {}).get("userid") or "").strip()
    chat_id = (body.get("chatid") or user_id or "").strip()
    msg_id = (body.get("msgid") or "").strip()
    chat_type = (body.get("chattype") or "single").strip()
    if not user_id or not chat_id:
        return None

    return WeComInboundMessage(
        chat_id=chat_id,
        user_id=user_id,
        msg_id=msg_id,
        content=text,
        chat_type=chat_type,
    )


def _to_session_id(message: WeComInboundMessage) -> str:
    if message.chat_type == "group":
        return f"wecom:group:{message.chat_id}:user:{message.user_id}"
    return f"wecom:user:{message.user_id}"


def _build_proactive_message() -> str:
    templates = [
        "刚刚有一点想你呢，就来戳你一下。",
        "突然想起你了，所以跟你说一声。",
        "刚才发了会儿呆，顺手想你一下呦。",
        "也没什么事，就是刚刚有点想你。",
        "今天这一小会儿，脑子里又晃到你了。",
        "嗯，路过想你一下，好呢。",
        "本来在忙点别的，还是忍不住想起你了。",
        "突然有点想你，跟你报备一下。",
    ]
    return random.choice(templates)


SCHEDULE_WINDOWS = {
    "morning": (time(9, 0), time(12, 0)),
    "afternoon": (time(15, 0), time(17, 0)),
    "evening": (time(19, 0), time(22, 0)),
}


class WeComMyLoverBot:
    def __init__(self, pipeline: MyLoverPipeline | None = None) -> None:
        if not settings.wecom_bot_id or not settings.wecom_bot_secret:
            raise ValueError("Missing WECOM_BOT_ID or WECOM_BOT_SECRET in environment")

        self.pipeline = pipeline or MyLoverPipeline()
        self.client = WSClient(
            bot_id=settings.wecom_bot_id,
            secret=settings.wecom_bot_secret,
            ws_url=settings.wecom_ws_url,
        )
        self.tz = ZoneInfo(settings.wecom_schedule_timezone)
        self.schedule_state_path = Path(settings.session_dir) / "_wecom_schedule.json"
        self._stop_event = asyncio.Event()
        self._reply_lock = asyncio.Lock()
        self._scheduler_task: asyncio.Task | None = None

        self.client.on("authenticated", self._on_authenticated)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("error", self._on_error)
        self.client.on("message.text", self._on_text_message)

    def _on_authenticated(self) -> None:
        print("[wecom] authenticated")

    def _on_disconnected(self, reason: str) -> None:
        print(f"[wecom] disconnected: {reason}")

    def _on_error(self, error: Exception) -> None:
        print(f"[wecom] error: {error}")

    def _read_schedule_state(self) -> dict[str, Any]:
        if not self.schedule_state_path.exists():
            return {}
        try:
            return json.loads(self.schedule_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_schedule_state(self, state: dict[str, Any]) -> None:
        self.schedule_state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_daily_schedule(self, today: str) -> dict[str, Any]:
        slots: dict[str, str] = {}
        for name, (start, end) in SCHEDULE_WINDOWS.items():
            start_minute = start.hour * 60 + start.minute
            end_minute = end.hour * 60 + end.minute - 1
            picked = random.randint(start_minute, end_minute)
            hour, minute = divmod(picked, 60)
            slots[name] = f"{hour:02d}:{minute:02d}"
        return {"date": today, "slots": slots, "sent": []}

    def _ensure_today_schedule(self) -> dict[str, Any]:
        today = datetime.now(self.tz).date().isoformat()
        state = self._read_schedule_state()
        if state.get("date") != today:
            state = self._build_daily_schedule(today)
            self._write_schedule_state(state)
            print(f"[wecom] scheduled proactive slots: {state['slots']}")
        return state

    def _record_proactive_message(self, content: str) -> None:
        if not settings.wecom_allowed_user_id:
            return
        session_id = f"wecom:user:{settings.wecom_allowed_user_id}"
        state = self.pipeline.load_state(session_id)
        state.last_agent_reply = content
        state.conversation_history = [*state.conversation_history, f"lover: {content}"]
        self.pipeline.save_state(state)

    async def _send_proactive_message(self, slot_name: str) -> None:
        if not settings.wecom_allowed_user_id:
            return
        content = _build_proactive_message()
        async with self._reply_lock:
            try:
                await self.client.send_message(
                    settings.wecom_allowed_user_id,
                    {
                        "msgtype": "text",
                        "text": {"content": content},
                    },
                )
                self._record_proactive_message(content)
                print(f"[wecom] proactive outbound slot={slot_name}: {content!r}")
            except Exception as exc:
                print(f"[wecom] proactive send failed slot={slot_name}: {exc}")

    async def _run_scheduler(self) -> None:
        while not self._stop_event.is_set():
            state = self._ensure_today_schedule()
            now = datetime.now(self.tz)
            now_hm = now.strftime("%H:%M")
            sent = set(state.get("sent", []))
            slots = state.get("slots", {})
            for slot_name, slot_time in slots.items():
                if slot_name in sent:
                    continue
                _, window_end = SCHEDULE_WINDOWS[slot_name]
                window_end_hm = f"{window_end.hour:02d}:{window_end.minute:02d}"
                if now_hm > window_end_hm:
                    sent.add(slot_name)
                    state["sent"] = sorted(sent)
                    self._write_schedule_state(state)
                    continue
                if slot_time <= now_hm <= window_end_hm:
                    await self._send_proactive_message(slot_name)
                    sent.add(slot_name)
                    state["sent"] = sorted(sent)
                    self._write_schedule_state(state)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                continue

    async def _on_text_message(self, frame: dict[str, Any]) -> None:
        message = _extract_text(frame)
        if message is None:
            return

        print(
            f"[wecom] inbound msg_id={message.msg_id} user={message.user_id} "
            f"chat={message.chat_id} type={message.chat_type} text={message.content!r}"
        )

        if (
            settings.wecom_allowed_user_id
            and message.user_id != settings.wecom_allowed_user_id
        ):
            print(
                f"[wecom] ignored message from unauthorized user: {message.user_id}"
            )
            return

        async with self._reply_lock:
            session_id = _to_session_id(message)
            try:
                reply, _, debug = await asyncio.to_thread(
                    self.pipeline.chat,
                    session_id,
                    message.content,
                )
                print(
                    f"[wecom] generated reply session={session_id} "
                    f"memory_written={debug.memory_written} reason={debug.memory_reason}"
                )
                try:
                    await self.client.send_message(
                        message.chat_id,
                        {
                            "msgtype": "markdown",
                            "markdown": {"content": reply},
                        },
                    )
                except Exception as send_exc:
                    print(f"[wecom] markdown send failed, fallback to text: {send_exc}")
                    await self.client.send_message(
                        message.chat_id,
                        {
                            "msgtype": "text",
                            "text": {"content": reply},
                        },
                    )
                print(f"[wecom] outbound to {message.user_id}: {reply!r}")
            except Exception as exc:
                print(f"[wecom] failed to handle message {message.msg_id}: {exc}")

    async def run(self) -> None:
        print(
            "[wecom] starting bot with "
            f"allowed_user={settings.wecom_allowed_user_id or '*'} "
            f"ws_url={settings.wecom_ws_url}"
        )
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stop_event.set)
            except NotImplementedError:
                pass

        await self.client.connect()
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        await self._stop_event.wait()
        if self._scheduler_task:
            self._scheduler_task.cancel()
            await asyncio.gather(self._scheduler_task, return_exceptions=True)
        await self.client.disconnect()
