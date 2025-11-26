from __future__ import annotations

from abc import ABC, abstractmethod

from .models import StrategyContext, TradeIntent


class TradingStrategy(ABC):
    @abstractmethod
    def decide(self, context: StrategyContext) -> TradeIntent:
        raise NotImplementedError
