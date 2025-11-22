 """Shared data models used across modules."""

 from __future__ import annotations

 from dataclasses import dataclass, field
 from datetime import datetime
 from enum import Enum
 from typing import Dict, List, Optional


 class TradeDirection(str, Enum):
     LONG = "long"
     SHORT = "short"
     FLAT = "flat"


 @dataclass(slots=True)
 class OHLCV:
     symbol: str
     interval: str
     open_time: datetime
     open: float
     high: float
     low: float
     close: float
     volume: float


 @dataclass(slots=True)
 class IndicatorSet:
     symbol: str
     interval: str
     timestamp: datetime
     ma: Dict[int, float] = field(default_factory=dict)
     ema: Dict[int, float] = field(default_factory=dict)
     macd: Dict[str, float] = field(default_factory=dict)
     rsi: Dict[int, float] = field(default_factory=dict)
     volume_ratio: Optional[float] = None


 @dataclass(slots=True)
 class SupportResistance:
     symbol: str
     interval: str
     timestamp: datetime
     support: float
     resistance: float
     confidence: float
     source: str  # "ai" or "rule"


 @dataclass(slots=True)
 class Signal:
     symbol: str
     direction: TradeDirection
     confidence: float
     reason: str
     timestamp: datetime
     metadata: Dict[str, float] = field(default_factory=dict)


 @dataclass(slots=True)
 class Position:
     symbol: str
     direction: TradeDirection
     size: float
     entry_price: float
     leverage: float
     open_time: datetime
     stop_loss: float
     take_profit: float
     support: Optional[float] = None
     resistance: Optional[float] = None


 @dataclass(slots=True)
 class AiEvaluation:
     action: str
     reason: str
     risk_level: str
     confidence: float
     raw_response: Dict


 @dataclass(slots=True)
 class StrategyState:
     current_position: Optional[Position] = None
     signal_history: List[Signal] = field(default_factory=list)
     ai_history: List[AiEvaluation] = field(default_factory=list)
     last_data_pull: Optional[datetime] = None
     last_minute_review: Optional[datetime] = None
