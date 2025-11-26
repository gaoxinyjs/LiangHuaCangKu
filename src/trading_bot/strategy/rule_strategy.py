from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_bot.ai.models import AISignal
from trading_bot.config.models import AppConfig
from trading_bot.execution.position import Position
from trading_bot.strategy.base import TradingStrategy
from trading_bot.strategy.models import StrategyContext, TradeIntent


@dataclass(slots=True)
class ConfidenceScaler:
    bands: tuple[float, ...]
    sizes: tuple[float, ...]

    def select_size(self, confidence: float) -> float:
        idx = 0
        for threshold in self.bands:
            if confidence < threshold:
                break
            idx += 1
        idx = min(idx, len(self.sizes) - 1)
        return self.sizes[idx]


class DeepSeekHybridStrategy(TradingStrategy):
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._scaler = ConfidenceScaler(
            bands=tuple(config.risk.confidence_bands),
            sizes=tuple(config.risk.position_sizes),
        )

    def decide(self, context: StrategyContext) -> TradeIntent:
        if context.active_position:
            return self._handle_position(context)
        return self._handle_entry(context)

    def _handle_position(self, context: StrategyContext) -> TradeIntent:
        assert context.active_position
        position = context.active_position
        mark = context.mark_price or position.entry_price
        pnl = position.unrealized_pnl(mark)
        hold_minutes = max(
            0,
            int(
                (datetime.utcnow() - position.opened_at).total_seconds() / 60
            ),
        )

        risk = self._config.risk
        toggles = self._config.toggles
        ai = context.ai_signal

        if self._should_force_exit(ai, pnl, hold_minutes, toggles.hold_min_minutes):
            return TradeIntent(action="close", reason="AI reversal risk or rule breach")

        if pnl >= 0 and ai.reversal_risk > 0.6:
            return TradeIntent(action="close", reason="Protect profit before reversal")

        if pnl < 0 and ai.direction_confidence < 0.3:
            return TradeIntent(action="close", reason="Low confidence on recovery")

        return TradeIntent(action="hold", reason="Holding per strategy rules")

    def _handle_entry(self, context: StrategyContext) -> TradeIntent:
        ai = context.ai_signal
        main_tf = context.features.indicators.get("1h") or next(iter(context.features.indicators.values()))
        values = main_tf.values
        momentum = values.get("ema_12", 0) - values.get("ema_26", 0)
        rsi = values.get("rsi", 50)

        direction: str | None = None
        if ai.direction_confidence >= 0.55 and momentum >= 0 and rsi < 70 and self._config.toggles.enable_long:
            direction = "long"
        elif ai.direction_confidence <= 0.45 and momentum <= 0 and rsi > 30 and self._config.toggles.enable_short:
            direction = "short"

        if not direction:
            return TradeIntent(action="hold", reason="No aligned entry signal")

        entry_price = values["close"]
        tp_ratio = self._config.risk.take_profit_pct / self._config.risk.leverage
        sl_ratio = self._config.risk.stop_loss_pct / self._config.risk.leverage

        take_profit = (
            entry_price * (1 + tp_ratio) if direction == "long" else entry_price * (1 - tp_ratio)
        )
        stop_loss = (
            entry_price * (1 - sl_ratio) if direction == "long" else entry_price * (1 + sl_ratio)
        )

        size = self._scaler.select_size(ai.direction_confidence)
        reason = f"{direction} entry via AI confidence {ai.direction_confidence:.2f}"
        return TradeIntent(
            action="open",
            direction=direction,
            entry_price=entry_price,
            size=size,
            take_profit=take_profit,
            stop_loss=stop_loss,
            reason=reason,
        )

    def _should_force_exit(
        self, ai: AISignal, pnl: float, hold_minutes: int, min_hold_minutes: int
    ) -> bool:
        if hold_minutes < min_hold_minutes and pnl >= 0:
            return False
        if ai.reversal_risk > 0.8:
            return True
        if pnl < 0 and ai.direction_confidence < 0.4:
            return True
        return False
