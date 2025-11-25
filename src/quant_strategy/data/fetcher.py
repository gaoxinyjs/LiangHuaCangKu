"""Market data fetching layer with retry and caching hooks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import httpx
from tenacity import Retrying, stop_after_attempt, wait_exponential

from quant_strategy.core.config import Config
from quant_strategy.core.models import OHLCV


class DataFetcher:
    """Retrieve OHLCV candles from the configured exchange REST API."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = httpx.Client(base_url=config.exchange.base_url, timeout=10.0)

    def _retrying(self) -> Retrying:
        return Retrying(
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(3),
            reraise=True,
        )

    def fetch_klines(self, symbol: str, interval: str, limit: Optional[int] = None) -> List[OHLCV]:
        limit = limit or self._config.data.history_limit
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        for attempt in self._retrying():
            with attempt:
                response = self._client.get("/api/v3/klines", params=params)
                response.raise_for_status()
                raw = response.json()
                return [self._parse_kline(symbol, interval, item) for item in raw]
        raise RuntimeError("Unreachable fetch_klines")

    @staticmethod
    def _parse_kline(symbol: str, interval: str, row: list) -> OHLCV:
        open_time = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc)
        return OHLCV(
            symbol=symbol,
            interval=interval,
            open_time=open_time,
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )

    def close(self) -> None:
        self._client.close()
