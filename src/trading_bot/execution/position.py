from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Position:
    symbol: str
    direction: str  # "long" or "short"
    entry_price: float
    size: float
    leverage: float
    opened_at: datetime
    take_profit: float
    stop_loss: float

    def unrealized_pnl(self, mark_price: float) -> float:
        sign = 1 if self.direction == "long" else -1
        return (mark_price - self.entry_price) * sign * self.size * self.leverage
