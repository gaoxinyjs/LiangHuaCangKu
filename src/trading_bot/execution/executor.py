from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from trading_bot.config.models import AppConfig
from trading_bot.execution.position import Position
from trading_bot.strategy.models import TradeIntent


@dataclass(slots=True)
class ExecutionReport:
    action: str
    message: str
    position: Optional[Position] = None
    realized_pnl: float | None = None
    orders: List["OrderFill"] = field(default_factory=list)
    total_fees: float | None = None


@dataclass(slots=True)
class OrderFill:
    order_id: str
    action: str  # open or close
    side: str  # buy or sell
    direction: str
    fill_price: float
    size: float
    fee_paid: float
    slippage_bps: float


class PortfolioExecutor:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._position: Optional[Position] = None

    @property
    def position(self) -> Optional[Position]:
        return self._position

    def execute(self, intent: TradeIntent, timestamp: datetime) -> ExecutionReport:
        orders: list[OrderFill] = []
        if intent.action == "hold":
            return ExecutionReport(
                action="hold",
                message=intent.reason,
                position=self._position,
                orders=orders,
            )

        if intent.action == "close":
            if not self._position:
                return ExecutionReport(
                    action="close", message="No position to close", orders=orders
                )
            pnl, order, total_fees = self._close_position(
                intent.entry_price or self._position.entry_price,
                intent.slippage_tolerance_bps,
            )
            orders.append(order)
            return ExecutionReport(
                action="close",
                message=intent.reason or "Manual close",
                realized_pnl=pnl,
                orders=orders,
                total_fees=total_fees,
            )

        if intent.action == "open":
            if not intent.direction or not intent.entry_price:
                return ExecutionReport(
                    action="hold", message="Incomplete open intent", orders=orders
                )

            logs = []
            if self._position:
                pnl, close_order, total_fees = self._close_position(
                    intent.entry_price,
                    intent.slippage_tolerance_bps,
                )
                orders.append(close_order)
                logs.append(
                    f"Closed existing position pnl={pnl:.2f} fees={total_fees:.4f}"
                )

            size = intent.size or self._config.risk.position_sizes[0]
            fill_price, slippage = self._apply_slippage(
                side="buy" if intent.direction == "long" else "sell",
                price=intent.entry_price,
                tolerance_bps=intent.slippage_tolerance_bps,
            )
            fee = self._calc_fee(fill_price, size)
            order = OrderFill(
                order_id=str(uuid4()),
                action="open",
                side="buy" if intent.direction == "long" else "sell",
                direction=intent.direction,
                fill_price=fill_price,
                size=size,
                fee_paid=fee,
                slippage_bps=slippage,
            )
            orders.append(order)

            self._position = Position(
                symbol=self._config.data.symbol,
                direction=intent.direction,
                entry_price=fill_price,
                size=size,
                leverage=self._config.risk.leverage,
                opened_at=timestamp,
                take_profit=intent.take_profit or intent.entry_price,
                stop_loss=intent.stop_loss or intent.entry_price,
                fees_paid=fee,
            )
            logs.append(
                f"Opened {self._position.direction} at {self._position.entry_price:.2f} "
                f"(slip {slippage:.2f}bps, fee {fee:.4f})"
            )
            return ExecutionReport(
                action="open",
                message=" | ".join(logs),
                position=self._position,
                orders=orders,
                total_fees=fee,
            )

        return ExecutionReport(action="hold", message="Unknown intent")

    def _close_position(
        self, exit_price: float, slippage_tolerance_bps: float | None
    ) -> tuple[float, OrderFill, float]:
        assert self._position
        side = "sell" if self._position.direction == "long" else "buy"
        fill_price, slippage = self._apply_slippage(
            side=side, price=exit_price, tolerance_bps=slippage_tolerance_bps
        )
        fee = self._calc_fee(fill_price, self._position.size)
        sign = 1 if self._position.direction == "long" else -1
        gross = (
            (fill_price - self._position.entry_price)
            * sign
            * self._position.size
            * self._position.leverage
        )
        total_fees = self._position.fees_paid + fee
        pnl = gross - total_fees
        order = OrderFill(
            order_id=str(uuid4()),
            action="close",
            side=side,
            direction=self._position.direction,
            fill_price=fill_price,
            size=self._position.size,
            fee_paid=fee,
            slippage_bps=slippage,
        )
        self._position = None
        return pnl, order, total_fees

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

    def _apply_slippage(
        self, side: str, price: float, tolerance_bps: float | None
    ) -> tuple[float, float]:
        tolerance = tolerance_bps if tolerance_bps is not None else self._config.risk.default_slippage_bps
        slippage_bps = max(0.0, tolerance * 0.5)
        direction = 1 if side == "buy" else -1
        fill_price = price * (1 + direction * slippage_bps / 10_000)
        return fill_price, slippage_bps

    def _calc_fee(self, price: float, size: float) -> float:
        notional = abs(price * size * self._config.risk.leverage)
        return notional * self._config.risk.taker_fee_rate
