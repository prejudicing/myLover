from __future__ import annotations

from textwrap import dedent


LANGGRAPH_BLUEPRINT = dedent(
    """
    Recommended LangGraph node split for the next phase:

    1. load_state
    2. retrieve_memory
    3. classify_user_signal
    4. update_relationship_state
    5. generate_reply
    6. decide_memory_writeback
    7. persist_state

    Why this maps cleanly from the MVP:
    - retrieval is already isolated in memory_store.py
    - classification and state update are already pure functions in pipeline.py
    - prompt construction is isolated in prompts.py
    - state schema is already explicit in schemas.py

    Minimal future graph state:
    - messages
    - relationship_state
    - retrieved_memories
    - user_signal
    - candidate_memory_write
    """
).strip()
