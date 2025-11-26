from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from trading_bot.ai.models import AISignal
from trading_bot.data.models import FeatureBundle


class AISignalProvider(ABC):
    @abstractmethod
    async def infer(self, features: FeatureBundle) -> AISignal:
        raise NotImplementedError
