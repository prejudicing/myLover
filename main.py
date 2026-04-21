from __future__ import annotations

import argparse

from src.mylover.pipeline import MyLoverPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="myLover MVP CLI")
    parser.add_argument("--message", required=True, help="User message")
    parser.add_argument("--session-id", default="local-demo", help="Session identifier")
    parser.add_argument("--show-prompt", action="store_true", help="Print prompt preview")
    parser.add_argument("--show-memories", action="store_true", help="Print retrieved memories")
    args = parser.parse_args()

    pipeline = MyLoverPipeline()
    reply, next_state, debug = pipeline.chat(args.session_id, args.message)

    print("reply:")
    print(reply)
    print("\nuser_signal:")
    print(debug.user_signal.model_dump_json(indent=2))
    if args.show_memories:
        print("\nretrieved_memories:")
        for memory in debug.retrieved_memories:
            print(f"- [{memory.memory_type}] {memory.content}")
    if args.show_prompt:
        print("\nprompt_preview:")
        print(debug.prompt_preview)
    print("\nstate:")
    print(next_state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
