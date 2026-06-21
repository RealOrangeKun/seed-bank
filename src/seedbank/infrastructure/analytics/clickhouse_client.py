"""Async ClickHouse client.

Used for the read path of `/stats`, `/models/{id}/performance`, and
experiment leaderboards. Writes flow in via the CDC worker (Phase 8).

`clickhouse-connect` exposes both a sync and an async API. We use the async
client for request paths and lean on its built-in connection pool.
"""

from __future__ import annotations

from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient

from seedbank.core.config import Settings, get_settings
from seedbank.core.exceptions import ExternalServiceError
from seedbank.core.logging import get_logger

log = get_logger(__name__)


class ClickHouseClient:
    """Thin wrapper. Encapsulates the underlying driver so callers don't
    couple to clickhouse_connect imports."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    @classmethod
    async def from_settings(cls, settings: Settings) -> "ClickHouseClient":
        client = await clickhouse_connect.get_async_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password.get_secret_value(),
            database=settings.clickhouse_database,
            connect_timeout=10,
            send_receive_timeout=30,
        )
        return cls(client)

    async def ping(self) -> bool:
        try:
            await self._client.query("SELECT 1")
            return True
        except Exception as exc:  # noqa: BLE001 — driver raises various
            log.warning("clickhouse.ping_failed", error=str(exc))
            return False

    async def query(
        self, sql: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        try:
            result = await self._client.query(sql, parameters=parameters)
            cols = result.column_names
            return [dict(zip(cols, row, strict=True)) for row in result.result_rows]
        except Exception as exc:
            raise ExternalServiceError(f"clickhouse query failed: {exc}") from exc

    async def execute(self, sql: str, parameters: dict[str, Any] | None = None) -> None:
        try:
            await self._client.command(sql, parameters=parameters)
        except Exception as exc:
            raise ExternalServiceError(f"clickhouse execute failed: {exc}") from exc

    async def insert(
        self,
        table: str,
        rows: list[list[Any]],
        column_names: list[str],
    ) -> None:
        """Bulk insert rows. Empty ``rows`` is a no-op so callers can use
        the same code path for empty result sets.

        Wrapping :class:`Exception` here because ``clickhouse-connect``
        raises a small zoo of driver-specific subclasses we don't want to
        catch individually in every dual-write task.
        """
        if not rows:
            return
        try:
            await self._client.insert(
                table=table,
                data=rows,
                column_names=column_names,
            )
        except Exception as exc:
            raise ExternalServiceError(f"clickhouse insert into {table!r} failed: {exc}") from exc

    async def close(self) -> None:
        await self._client.close()


_client: ClickHouseClient | None = None


async def get_clickhouse() -> ClickHouseClient:
    """Lazy-initialized process-wide ClickHouse client."""
    global _client
    if _client is None:
        _client = await ClickHouseClient.from_settings(get_settings())
    return _client


async def close_clickhouse() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
