from __future__ import annotations

import asyncio

from src.mylover.wecom_bot import WeComMyLoverBot


def main() -> None:
    asyncio.run(WeComMyLoverBot().run())


if __name__ == "__main__":
    main()
