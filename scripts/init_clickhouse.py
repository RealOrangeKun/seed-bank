"""Thin CLI wrapper around the DWH bootstrap.

Run with ``python -m scripts.init_clickhouse``. Idempotent — safe to call
on every container start.

The orchestration lives in :func:`seedbank.bootstrap.bootstrap_clickhouse`
so it can be unit-tested and reused (e.g. by ``seed_dev``).
"""

from __future__ import annotations

import asyncio
import sys

from seedbank.bootstrap import bootstrap_clickhouse
from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger

log = get_logger("seedbank.init_clickhouse")


async def main() -> int:
    settings = get_settings()
    n = await bootstrap_clickhouse(settings)
    log.info("init_clickhouse.done", seed_types_mirrored=n)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
