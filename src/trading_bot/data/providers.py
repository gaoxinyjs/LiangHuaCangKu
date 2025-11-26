from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Sequence

from .models import Candle, MarketSnapshot
from .provider_base import MarketDataProvider, TimeProvider


class SystemTimeProvider(TimeProvider):
    def now(self) -> datetime:
        return datetime.utcnow()


class MockMarketDataProvider(MarketDataProvider):
    """Simple provider that synthesizes candles for testing."""

    def __init__(self, time_source: TimeProvider | None = None, time_provider: TimeProvider | None = None) -> None:
        # time_provider 参数用于兼容不同命名写法
        provider = time_provider or time_source
        self._time_source = provider or SystemTimeProvider()

    async def fetch_snapshot(
        self, symbol: str, timeframe: str, lookback: int
    ) -> MarketSnapshot:
        now = self._time_source.now()
        minutes = _parse_minutes(timeframe)
        candles: list[Candle] = []
        price = 60000.0
        for i in reversed(range(lookback)):
            ts = now - timedelta(minutes=minutes * i)
            drift = random.uniform(-100, 100)
            open_price = price + drift
            high = open_price + random.uniform(0, 50)
            low = open_price - random.uniform(0, 50)
            close = random.uniform(low, high)
            volume = random.uniform(10, 1000)
            vwap = (high + low + close) / 3
            price = close
            candles.append(
                Candle(
                    timestamp=ts,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    vwap=vwap,
                )
            )
        return MarketSnapshot(symbol=symbol, timeframe=timeframe, candles=candles)


def _parse_minutes(label: str) -> int:
    unit = label[-1]
    value = int(label[:-1])
    multiplier = {"m": 1, "h": 60, "d": 1440}[unit]
    return value * multiplier
