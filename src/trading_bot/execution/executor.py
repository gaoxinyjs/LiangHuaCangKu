from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from trading_bot.config.models import AppConfig
from trading_bot.execution.position import Position
from trading_bot.strategy.models import TradeIntent


@dataclass(slots=True)
class ExecutionReport:
    action: str
    message: str
    position: Optional[Position] = None
    realized_pnl: float | None = None


class PortfolioExecutor:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._position: Optional[Position] = None

    @property
    def position(self) -> Optional[Position]:
        return self._position

    def execute(self, intent: TradeIntent, timestamp: datetime) -> ExecutionReport:
        if intent.action == "hold":
            return ExecutionReport(action="hold", message=intent.reason, position=self._position)

        if intent.action == "close":
            if not self._position:
                return ExecutionReport(action="close", message="No position to close")
            pnl = self._close_position(intent.entry_price or self._position.entry_price)
            return ExecutionReport(
                action="close",
                message=intent.reason or "Manual close",
                realized_pnl=pnl,
            )

        if intent.action == "open":
            if not intent.direction or not intent.entry_price:
                return ExecutionReport(action="hold", message="Incomplete open intent")

            logs = []
            if self._position:
                pnl = self._close_position(intent.entry_price)
                logs.append(f"Closed existing position pnl={pnl:.2f}")

            self._position = Position(
                symbol=self._config.data.symbol,
                direction=intent.direction,
                entry_price=intent.entry_price,
                size=intent.size or self._config.risk.position_sizes[0],
                leverage=self._config.risk.leverage,
                opened_at=timestamp,
                take_profit=intent.take_profit or intent.entry_price,
                stop_loss=intent.stop_loss or intent.entry_price,
            )
            logs.append(f"Opened {self._position.direction} at {self._position.entry_price:.2f}")
            return ExecutionReport(action="open", message=" | ".join(logs), position=self._position)

        return ExecutionReport(action="hold", message="Unknown intent")

    def _close_position(self, exit_price: float) -> float:
        assert self._position
        pnl = self._position.unrealized_pnl(exit_price)
        self._position = None
        return pnl

    def needs_force_close(self, now: datetime) -> bool:
        if not self._position:
            return False
        session_end = self._config.scheduling.session_end
        limit_dt = now.replace(
            hour=session_end.hour,
            minute=session_end.minute,
            second=0,
            microsecond=0,
        )
        buffer = timedelta(minutes=self._config.scheduling.force_close_buffer_minutes)
        if now < limit_dt - buffer:
            return False
        return True
