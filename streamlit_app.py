from __future__ import annotations

import html

import streamlit as st

from src.mylover.pipeline import MyLoverPipeline


st.set_page_config(
    page_title="myLover",
    page_icon="💬",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700&family=Inter:wght@400;500;600&display=swap');
    .stApp {
      background:
        radial-gradient(circle at top left, rgba(240, 157, 92, 0.24), transparent 24%),
        radial-gradient(circle at bottom right, rgba(113, 149, 196, 0.22), transparent 26%),
        linear-gradient(180deg, #f6efe6 0%, #eadccc 100%);
      font-family: "Inter", sans-serif;
    }
    .block-container {
      max-width: 1120px;
      padding-top: 1.2rem;
      padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #30251f 0%, #221a16 100%);
      border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] * {
      color: #f5eee6;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.2rem;
      border: 1px solid rgba(72, 54, 38, 0.12);
      background: rgba(255, 250, 244, 0.78);
      backdrop-filter: blur(12px);
      border-radius: 24px;
      margin-bottom: 1rem;
    }
    .title {
      font-family: "Noto Serif SC", serif;
      font-size: 2rem;
      margin: 0;
      color: #403125;
    }
    .subtitle {
      margin: 0.3rem 0 0;
      color: #6b5847;
    }
    .presence {
      padding: 0.55rem 0.9rem;
      border-radius: 999px;
      background: #f1e3d1;
      color: #6b5847;
      font-size: 0.92rem;
    }
    .chat-shell {
      border: 1px solid rgba(72, 54, 38, 0.12);
      background: rgba(255, 251, 247, 0.76);
      backdrop-filter: blur(12px);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 18px 48px rgba(67, 46, 24, 0.08);
    }
    .chat-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.2rem;
      background: linear-gradient(180deg, rgba(255,255,255,0.68), rgba(246,236,224,0.68));
      border-bottom: 1px solid rgba(72, 54, 38, 0.1);
    }
    .chat-header-left {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .avatar {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #d48f62, #c76f63);
      color: white;
      font-weight: 700;
    }
    .chat-name {
      font-weight: 700;
      color: #433126;
    }
    .chat-note {
      font-size: 0.9rem;
      color: #7d6656;
      margin-top: 0.15rem;
    }
    .chat-body {
      padding: 1rem 1rem 1.2rem;
      min-height: 62vh;
      max-height: 62vh;
      overflow-y: auto;
      background:
        linear-gradient(rgba(255,255,255,0.4), rgba(255,255,255,0.4)),
        radial-gradient(circle at 1px 1px, rgba(112, 82, 53, 0.06) 1px, transparent 0);
      background-size: auto, 22px 22px;
    }
    .msg-row {
      display: flex;
      margin: 0.5rem 0;
    }
    .msg-row.user {
      justify-content: flex-end;
    }
    .msg-row.assistant {
      justify-content: flex-start;
    }
    .bubble {
      max-width: 72%;
      padding: 0.82rem 0.96rem;
      border-radius: 18px;
      line-height: 1.55;
      font-size: 0.98rem;
      white-space: pre-wrap;
      box-shadow: 0 10px 24px rgba(67, 46, 24, 0.06);
    }
    .bubble.user {
      background: linear-gradient(180deg, #d77f52 0%, #ca6c4f 100%);
      color: #fff9f5;
      border-bottom-right-radius: 6px;
    }
    .bubble.assistant {
      background: #fffaf5;
      color: #4a392d;
      border: 1px solid rgba(72, 54, 38, 0.1);
      border-bottom-left-radius: 6px;
    }
    .panel {
      border: 1px solid rgba(72, 54, 38, 0.12);
      background: rgba(255, 249, 243, 0.72);
      border-radius: 24px;
      padding: 1rem;
      box-shadow: 0 12px 32px rgba(67, 46, 24, 0.05);
    }
    .mini-label {
      font-size: 0.82rem;
      color: #8d7462;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pipeline = MyLoverPipeline()

if "session_id" not in st.session_state:
    existing = [name for name in pipeline.list_sessions() if name != "default"]
    st.session_state.session_id = existing[-1] if existing else "demo"

st.markdown(
    f"""
    <div class="topbar">
      <div>
        <div class="title">myLover</div>
        <div class="subtitle">更像聊天产品的对话界面，记忆写入已做筛选和去重。</div>
      </div>
      <div class="presence">当前会话：{html.escape(st.session_state.session_id)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

sidebar_sessions = [name for name in pipeline.list_sessions() if name != "default"]
with st.sidebar:
    st.subheader("会话")
    new_session = st.text_input("新会话名", placeholder="例如：qiaoqiao-demo")
    if st.button("创建 / 切换会话", use_container_width=True):
        target = (new_session or "demo").strip()
        st.session_state.session_id = target
        st.rerun()

    if sidebar_sessions:
        selected = st.selectbox(
            "历史会话",
            options=sidebar_sessions,
            index=sidebar_sessions.index(st.session_state.session_id)
            if st.session_state.session_id in sidebar_sessions
            else 0,
        )
        if selected != st.session_state.session_id:
            st.session_state.session_id = selected
            st.rerun()

    st.caption(f"当前会话：`{st.session_state.session_id}`")

state = pipeline.load_state(st.session_state.session_id)

col_chat, col_debug = st.columns([2.1, 1], gap="large")

with col_chat:
    st.markdown(
        """
        <div class="chat-shell">
          <div class="chat-header">
            <div class="chat-header-left">
              <div class="avatar">A</div>
              <div>
                <div class="chat-name">A是巧巧儿呢～</div>
                <div class="chat-note">有点累，偶尔回避，但会记得生活里的小事</div>
              </div>
            </div>
            <div class="chat-note">本地持久对话</div>
          </div>
          <div class="chat-body">
        """,
        unsafe_allow_html=True,
    )
    for role, content in pipeline.iter_messages(state):
        safe_role = "user" if role == "user" else "assistant"
        safe_content = html.escape(content)
        st.markdown(
            f"""
            <div class="msg-row {safe_role}">
              <div class="bubble {safe_role}">{safe_content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)

    prompt = st.chat_input("发一句话试试")
    if prompt:
        with st.spinner("正在回她..."):
            reply, state, debug = pipeline.chat(st.session_state.session_id, prompt)
        st.session_state["last_debug"] = debug.model_dump()
        st.rerun()

with col_debug:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("调试")
    latest_debug = st.session_state.get("last_debug")
    st.metric("已存记忆", pipeline.memory_store.count())
    st.metric("关系温度", f"{state.relationship_temperature:.2f}")
    st.metric("亲密压力", f"{state.user_intimacy_pressure:.2f}")
    if latest_debug:
        st.caption(
            f"记忆写入：{'已写入' if latest_debug.get('memory_written') else '已跳过'}"
            f" · 原因：{latest_debug.get('memory_reason', '-')}"
        )
    if latest_debug:
        st.caption("最近一次检索")
        for memory in latest_debug["retrieved_memories"]:
            st.markdown(f"- `[{memory['speaker']}:{memory['memory_type']}]` {memory['content']}")
    else:
        st.caption("还没有本轮调试数据。")
    st.markdown("</div>", unsafe_allow_html=True)
