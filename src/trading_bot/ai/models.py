from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(slots=True)
class SupportResistance:
    support: float
    resistance: float
    confidence: float


@dataclass(slots=True)
class AISignal:
    generated_at: datetime
    direction_confidence: float  # 0-1 bullish vs bearish threshold handled by strategy
    reversal_risk: float  # 0-1 probability of near-term reversal
    sr_levels: SupportResistance
    narrative: str = ""
