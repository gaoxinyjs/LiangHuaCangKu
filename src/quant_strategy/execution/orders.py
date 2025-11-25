"""Order sizing and risk helper utilities."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_strategy.core.config import RiskConfig
from quant_strategy.core.models import Position, Signal, TradeDirection


class OrderPlanner:
    """Translate signals into concrete position plans."""

    def __init__(self, risk_cfg: RiskConfig) -> None:
        self._risk = risk_cfg

    def create_position(
        self, signal: Signal, account_equity: float, price: float, volatility: float | None = None
    ) -> Position:
        if price <= 0:
            raise ValueError("Price must be positive to create a position.")

        atr_pct = None
        if self._risk.use_atr_targets and volatility and volatility > 0:
            atr_pct = max(volatility / price, 1e-9)

        take_profit_pct = (
            atr_pct * self._risk.atr_take_profit_multiplier if atr_pct else self._risk.take_profit_pct
        )
        stop_loss_pct = (
            atr_pct * self._risk.atr_stop_loss_multiplier if atr_pct else self._risk.stop_loss_pct
        )

        take_profit = self._calc_target(price, take_profit_pct, signal.direction, True)
        stop_loss = self._calc_target(price, stop_loss_pct, signal.direction, False)

        stop_distance = abs(price - stop_loss)
        max_conf_bucket = max(self._risk.confidence_buckets[-1], 1e-6)
        confidence_scale = min(signal.confidence / max_conf_bucket, 1.0)
        risk_capital = account_equity * self._risk.risk_per_trade_pct * confidence_scale

        if stop_distance <= 0:
            size = account_equity * confidence_scale * self._risk.leverage / price
        else:
            size = risk_capital / stop_distance

        max_units = account_equity * self._risk.leverage / price
        size = max(min(size, max_units), 0.0)

        position = Position(
            symbol=signal.symbol,
            direction=signal.direction,
            size=size,
            entry_price=price,
            leverage=self._risk.leverage,
            open_time=datetime.now(tz=timezone.utc),
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return position

    def _calc_target(
        self,
        price: float,
        pct: float,
        direction: TradeDirection,
        is_take_profit: bool,
    ) -> float:
        if pct <= 0 or price <= 0:
            return price
        delta = pct
        if direction == TradeDirection.LONG:
            return price * (1 + delta if is_take_profit else 1 - delta)
        if direction == TradeDirection.SHORT:
            return price * (1 - delta if is_take_profit else 1 + delta)
        return price
