from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Sequence


@dataclass(slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    timeframe: str
    candles: Sequence[Candle]

    def latest(self) -> Candle:
        return self.candles[-1]


@dataclass(slots=True)
class IndicatorSnapshot:
    timeframe: str
    values: Dict[str, float]


@dataclass(slots=True)
class FeatureBundle:
    symbol: str
    created_at: datetime
    indicators: Dict[str, IndicatorSnapshot] = field(default_factory=dict)
