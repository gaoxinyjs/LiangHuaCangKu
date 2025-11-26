from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from .models import MarketSnapshot


class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch_snapshot(
        self, symbol: str, timeframe: str, lookback: int
    ) -> MarketSnapshot:
        raise NotImplementedError


class TimeProvider(ABC):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError
