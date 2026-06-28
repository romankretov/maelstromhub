from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx


@dataclass(frozen=True)
class ProviderCandle:
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int | None = None


class DataProvider(ABC):
    name: str


class CandleProvider(DataProvider):
    @abstractmethod
    async def get_historical_candles(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[ProviderCandle]:
        pass


class HyperliquidCandleProvider(CandleProvider):
    name = "hyperliquid"

    def __init__(self, base_url: str = "https://api.hyperliquid.xyz") -> None:
        self.base_url = base_url

    async def get_historical_candles(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[ProviderCandle]:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol.upper(),
                "interval": interval,
                "startTime": int(start_time.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000),
            },
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20) as client:
            response = await client.post("/info", json=payload)
            response.raise_for_status()
            raw_candles = response.json()

        if not isinstance(raw_candles, list):
            raise ValueError("Hyperliquid candle response was not a list")

        return [self._parse_candle(item) for item in raw_candles]

    def _parse_candle(self, item: dict[str, Any]) -> ProviderCandle:
        opened_ms = item.get("t") or item.get("T")
        if opened_ms is None:
            raise ValueError("Hyperliquid candle missing timestamp")

        return ProviderCandle(
            opened_at=datetime.fromtimestamp(int(opened_ms) / 1000, tz=UTC),
            open=float(item["o"]),
            high=float(item["h"]),
            low=float(item["l"]),
            close=float(item["c"]),
            volume=float(item["v"]),
            trade_count=int(item["n"]) if item.get("n") is not None else None,
        )


def default_backfill_window() -> tuple[datetime, datetime]:
    end_time = datetime.now(UTC)
    return end_time - timedelta(days=7), end_time


async def get_candle_provider() -> CandleProvider:
    return HyperliquidCandleProvider()
