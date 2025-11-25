"""Execute planned trades (simulated) and handle lifecycle bookkeeping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from quant_strategy.core.models import Position, TradeDirection
from quant_strategy.execution.state_machine import StrategyStateMachine
from quant_strategy.monitoring.logger import StrategyLogger


class TradeExecutor:
    """Simple executor that records openings/closings via the state machine."""

    def __init__(self, state_machine: StrategyStateMachine, logger: StrategyLogger) -> None:
        self._state_machine = state_machine
        self._logger = logger

    def open_position(self, position: Position) -> None:
        """Register the new position and emit a log for operators."""
        self._state_machine.enter_position(position)
        self._logger.success(
            "Position opened",
            details={
                "symbol": position.symbol,
                "direction": position.direction.value,
                "size": f"{position.size:.4f}",
                "entry_price": f"{position.entry_price:.2f}",
                "take_profit": f"{position.take_profit:.2f}",
                "stop_loss": f"{position.stop_loss:.2f}",
            },
        )
        self._logger.log_position(position)

    def close_position(
        self,
        *,
        reason: str,
        exit_price: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Close the active position (if any) and log PnL stats."""
        position = self._state_machine.state.current_position
        if position is None:
            self._logger.warning(
                "Close requested but no active position",
                details={"reason": reason},
            )
            return

        timestamp = timestamp or datetime.now(tz=timezone.utc)
        price = exit_price if exit_price is not None else position.entry_price
        pnl = self._calculate_pnl(position, price)
        holding_minutes = (timestamp - position.open_time).total_seconds() / 60

        self._state_machine.exit_position()
        level = "success" if pnl >= 0 else "warning"
        self._logger.log_event(
            "Position closed",
            level=level,
            details={
                "symbol": position.symbol,
                "reason": reason,
                "exit_price": f"{price:.2f}",
                "pnl": f"{pnl:.2f}",
                "holding_min": f"{holding_minutes:.1f}",
            },
        )

    def _calculate_pnl(self, position: Position, exit_price: float) -> float:
        direction = self._direction_multiplier(position.direction)
        return direction * (exit_price - position.entry_price) * position.size

    def _direction_multiplier(self, direction: TradeDirection) -> float:
        if direction == TradeDirection.LONG:
            return 1.0
        if direction == TradeDirection.SHORT:
            return -1.0
        return 0.0
