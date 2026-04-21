from __future__ import annotations

import argparse

from src.mylover.pipeline import MyLoverPipeline
from src.mylover.schemas import RelationshipState


def main() -> None:
    parser = argparse.ArgumentParser(description="myLover MVP CLI")
    parser.add_argument("--message", required=True, help="User message")
    parser.add_argument("--session-id", default="local-demo", help="Session identifier")
    args = parser.parse_args()

    pipeline = MyLoverPipeline()
    initial_state = RelationshipState(session_id=args.session_id)
    reply, next_state = pipeline.invoke(initial_state, args.message)

    print("reply:")
    print(reply)
    print("\nstate:")
    print(next_state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
