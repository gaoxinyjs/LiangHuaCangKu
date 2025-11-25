"""Structured logging helpers using Rich."""

from __future__ import annotations

from typing import Any, Mapping

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from quant_strategy.core.models import AiEvaluation, Position, Signal


class StrategyLogger:
    _LEVEL_STYLES = {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }

    def __init__(self) -> None:
        self._console = Console()

    def log_event(
        self,
        message: str,
        *,
        level: str = "info",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        """Render a short status message (optionally with structured details)."""
        style = self._LEVEL_STYLES.get(level, "white")
        if details:
            table = Table.grid(expand=True)
            table.add_column(justify="right", style="bold")
            table.add_column(ratio=1)
            for key, value in details.items():
                table.add_row(str(key), str(value))
            panel = Panel(table, title=f"[bold]{message}", border_style=style)
            self._console.print(panel)
            return
        self._console.print(f"[bold {style}]{message}[/bold {style}]")

    def info(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.log_event(message, level="info", details=details)

    def success(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.log_event(message, level="success", details=details)

    def warning(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.log_event(message, level="warning", details=details)

    def error(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.log_event(message, level="error", details=details)

    def log_signal(self, signal: Signal) -> None:
        table = Table(title=f"Signal {signal.symbol}", show_lines=True)
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Direction", signal.direction.value)
        table.add_row("Confidence", f"{signal.confidence:.3f}")
        table.add_row("Score", f"{signal.metadata.get('score', 0.0):.3f}")
        table.add_row("MACD Hist", f"{signal.metadata.get('macd_hist', 0.0):.4f}")
        table.add_row("Vol Ratio", f"{signal.metadata.get('volume_ratio', 0.0):.2f}")
        table.add_row("ATR", f"{signal.metadata.get('atr', 0.0):.2f}")
        table.add_row("Reason", signal.reason)
        self._console.print(table)

    def log_position(self, position: Position) -> None:
        table = Table(title=f"Position {position.symbol}", show_lines=True)
        for field, value in [
            ("Direction", position.direction.value),
            ("Size", f"{position.size:.4f}"),
            ("Entry", f"{position.entry_price:.2f}"),
            ("TP", f"{position.take_profit:.2f}"),
            ("SL", f"{position.stop_loss:.2f}"),
        ]:
            table.add_row(field, value)
        self._console.print(table)

    def log_ai(self, evaluation: AiEvaluation) -> None:
        table = Table(title="DeepSeek Review", show_lines=True)
        table.add_row("Action", evaluation.action)
        table.add_row("Confidence", f"{evaluation.confidence:.2f}")
        table.add_row("Risk", evaluation.risk_level)
        table.add_row("Reason", evaluation.reason)
        self._console.print(table)
