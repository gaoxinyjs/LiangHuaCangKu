from __future__ import annotations

import random
from datetime import datetime

from trading_bot.ai.base import AISignalProvider
from trading_bot.ai.models import AISignal, SupportResistance
from trading_bot.data.models import FeatureBundle


class DeepSeekStub(AISignalProvider):
    """Placeholder for the real DeepSeek integration."""

    async def infer(self, features: FeatureBundle) -> AISignal:
        latest_tf = max(features.indicators.keys(), key=lambda tf: features.indicators[tf].values["close"])
        last_close = features.indicators[latest_tf].values["close"]
        drift = random.uniform(-0.01, 0.01)
        support = last_close * (1 - 0.02 + drift)
        resistance = last_close * (1 + 0.02 + drift)
        direction_confidence = random.random()
        reversal_risk = random.uniform(0, 0.5)
        return AISignal(
            generated_at=datetime.utcnow(),
            direction_confidence=direction_confidence,
            reversal_risk=reversal_risk,
            sr_levels=SupportResistance(
                support=support,
                resistance=resistance,
                confidence=random.uniform(0.3, 0.9),
            ),
            narrative="Synthetic DeepSeek signal",
        )
