from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from trading_bot.ai.models import AISignal
from trading_bot.config.models import AppConfig
from trading_bot.data.models import FeatureBundle
from trading_bot.execution.position import Position

DecisionAction = Literal["open", "close", "hold"]


@dataclass(slots=True)
class StrategyContext:
    config: AppConfig
    features: FeatureBundle
    ai_signal: AISignal
    active_position: Optional[Position] = None
    mark_price: float | None = None


@dataclass(slots=True)
class TradeIntent:
    action: DecisionAction
    direction: Literal["long", "short"] | None = None
    entry_price: float | None = None
    size: float | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    reason: str = ""
