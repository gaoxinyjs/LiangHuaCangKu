from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Dict, Sequence


@dataclass(slots=True)
class TimeframeConfig:
    label: str
    minutes: int
    lookback: int = 200


@dataclass(slots=True)
class DataConfig:
    symbol: str = "BTCUSDT"
    timeframes: Sequence[TimeframeConfig] = field(
        default_factory=lambda: (
            TimeframeConfig("15m", 15, 200),
            TimeframeConfig("1h", 60, 200),
            TimeframeConfig("4h", 240, 200),
            TimeframeConfig("1d", 1440, 200),
        )
    )


@dataclass(slots=True)
class RiskConfig:
    leverage: float = 5.0
    take_profit_pct: float = 0.06
    stop_loss_pct: float = 0.03
    confidence_bands: Sequence[float] = (0.2, 0.4, 0.6, 0.8)
    position_sizes: Sequence[float] = (0.05, 0.08, 0.10, 0.12, 0.15)


@dataclass(slots=True)
class SchedulingConfig:
    data_pull_minutes: int = 15
    position_poll_seconds: int = 60
    force_close_buffer_minutes: int = 15
    session_end: time = time(23, 45)


@dataclass(slots=True)
class StrategyToggles:
    enable_long: bool = True
    enable_short: bool = True
    hold_min_minutes: int = 3


@dataclass(slots=True)
class AppConfig:
    data: DataConfig = field(default_factory=DataConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    toggles: StrategyToggles = field(default_factory=StrategyToggles)
    metadata: Dict[str, str] = field(default_factory=dict)


def default_config() -> AppConfig:
    return AppConfig()
