 """Order sizing and risk helper utilities."""

 from __future__ import annotations

 from datetime import datetime, timezone

 from quant_strategy.core.config import RiskConfig
 from quant_strategy.core.models import Position, Signal, TradeDirection


 class OrderPlanner:
     """Translate signals into concrete position plans."""

     def __init__(self, risk_cfg: RiskConfig) -> None:
         self._risk = risk_cfg

     def create_position(self, signal: Signal, account_equity: float, price: float) -> Position:
         size = account_equity * signal.confidence * self._risk.leverage / price

         take_profit = self._calc_target(price, self._risk.take_profit_pct, signal.direction, True)
         stop_loss = self._calc_target(price, self._risk.stop_loss_pct, signal.direction, False)

         return Position(
             symbol=signal.symbol,
             direction=signal.direction,
             size=size,
             entry_price=price,
             leverage=self._risk.leverage,
             open_time=datetime.now(tz=timezone.utc),
             stop_loss=stop_loss,
             take_profit=take_profit,
         )

     def _calc_target(self, price: float, pct: float, direction: TradeDirection, is_take_profit: bool) -> float:
         delta = pct / max(self._risk.leverage, 1)
         if direction == TradeDirection.LONG:
             return price * (1 + delta if is_take_profit else 1 - delta)
         elif direction == TradeDirection.SHORT:
             return price * (1 - delta if is_take_profit else 1 + delta)
         return price
