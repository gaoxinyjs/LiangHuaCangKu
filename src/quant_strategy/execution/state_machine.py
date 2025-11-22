 """Strategy state machine to manage lifecycle from idle to close."""

 from __future__ import annotations

 from dataclasses import dataclass
 from datetime import datetime, timezone

 from quant_strategy.core.config import RiskConfig
 from quant_strategy.core.models import Position, StrategyState, TradeDirection


 class StrategyStateMachine:
     """Maintain transitions and enforce forced close rules."""

     def __init__(self, risk_cfg: RiskConfig) -> None:
         self._risk = risk_cfg
         self._state = StrategyState()

     @property
     def state(self) -> StrategyState:
         return self._state

     def enter_position(self, position: Position) -> None:
         self._state.current_position = position

     def exit_position(self) -> None:
         self._state.current_position = None

     def should_force_close(self, now: datetime, minutes_to_close: int) -> bool:
         if not self._state.current_position:
             return False
         if minutes_to_close <= self._risk.forced_close_minutes_before_eod:
             return True
         delta = now - self._state.current_position.open_time
         return delta.total_seconds() / 60 >= self._risk.max_position_minutes

     def needs_minute_review(self, now: datetime) -> bool:
         last = self._state.last_minute_review
         if last is None:
             return True
         return (now - last).total_seconds() >= 60

     def mark_minute_review(self, now: datetime) -> None:
         self._state.last_minute_review = now
