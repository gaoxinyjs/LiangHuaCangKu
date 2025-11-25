"""Helpers to assemble rich context for AI decision making."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from quant_strategy.core.config import RiskConfig
from quant_strategy.core.models import IndicatorSet, Position, Signal, TradeDirection


class StrategyContextBuilder:
    """Track latest market snapshots per symbol and prepare AI payloads."""

    def __init__(self, risk_cfg: RiskConfig | None = None) -> None:
        self._latest_indicators: Dict[str, IndicatorSet] = {}
        self._latest_signals: Dict[str, Signal] = {}
        self._risk_cfg = risk_cfg

    def update_market_snapshot(self, indicator: IndicatorSet, signal: Optional[Signal] = None) -> None:
        """Cache the freshest indicator/signal pair for later AI calls."""
        self._latest_indicators[indicator.symbol] = indicator
        if signal:
            self._latest_signals[indicator.symbol] = signal

    def build_ai_payload(self, position: Position) -> Dict[str, Any]:
        """Construct the DeepSeek payload with position and market context."""
        now = datetime.now(tz=timezone.utc)
        indicator = self._latest_indicators.get(position.symbol)
        signal = self._latest_signals.get(position.symbol)

        current_price = indicator.close if indicator else position.entry_price
        direction_mult = self._direction_multiplier(position)
        unrealized = direction_mult * (current_price - position.entry_price) * position.size

        payload: Dict[str, Any] = {
            "symbol": position.symbol,
            "direction": position.direction.value,
            "entry_price": position.entry_price,
            "take_profit": position.take_profit,
            "stop_loss": position.stop_loss,
            "size": position.size,
            "current_price": current_price,
            "holding_minutes": (now - position.open_time).total_seconds() / 60,
            "unrealized_pnl": unrealized,
        }

        if indicator:
            payload["market_snapshot"] = {
                "timestamp": indicator.timestamp.isoformat(),
                "interval": indicator.interval,
                "close": indicator.close,
                "atr": indicator.atr,
                "volume_ratio": indicator.volume_ratio,
                "macd": indicator.macd,
                "ma": indicator.ma,
                "ema": indicator.ema,
                "rsi": indicator.rsi,
            }

        if signal:
            payload["latest_signal"] = {
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "generated_at": signal.timestamp.isoformat(),
            }

        if self._risk_cfg:
            payload["risk_constraints"] = {
                "leverage": self._risk_cfg.leverage,
                "take_profit_pct": self._risk_cfg.take_profit_pct,
                "stop_loss_pct": self._risk_cfg.stop_loss_pct,
                "max_position_minutes": self._risk_cfg.max_position_minutes,
                "use_atr_targets": self._risk_cfg.use_atr_targets,
            }

        return payload

    def _direction_multiplier(self, position: Position) -> float:
        if position.direction == TradeDirection.LONG:
            return 1.0
        if position.direction == TradeDirection.SHORT:
            return -1.0
        return 0.0
