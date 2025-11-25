"""High-level orchestration tasks for cron/minutely runners."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from quant_strategy.ai.deepseek_client import DeepSeekClient
from quant_strategy.core.config import Config
from quant_strategy.core.models import Signal, TradeDirection
from quant_strategy.data.fetcher import DataFetcher
from quant_strategy.execution.orders import OrderPlanner
from quant_strategy.execution.state_machine import StrategyStateMachine
from quant_strategy.indicators.calculator import IndicatorCalculator
from quant_strategy.monitoring.logger import StrategyLogger
from quant_strategy.signals.context import StrategyContextBuilder
from quant_strategy.signals.evaluator import SignalEvaluator


class StrategyTasks:
    """Encapsulate periodic jobs (15m data pull, 1m AI review)."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._fetcher = DataFetcher(config)
        self._indicator_calc = IndicatorCalculator(config.indicators)
        self._signal_eval = SignalEvaluator(config.risk)
        self._order_planner = OrderPlanner(config.risk)
        self._ai_client = DeepSeekClient(config.ai)
        self._state_machine = StrategyStateMachine(config.risk)
        self._logger = StrategyLogger()
        self._context_builder = StrategyContextBuilder(config.risk)

    def run_data_cycle(self) -> None:
        """15m job: pull data, compute indicators, pick best signal, plan orders."""
        self._logger.info(
            "Starting data cycle",
            details={
                "task": "data_cycle",
                "interval": "15m",
                "symbols": ", ".join(self._config.data.symbols),
            },
        )
        candidates: List[Signal] = []
        for symbol in self._config.data.symbols:
            self._logger.info(
                "Fetching market data",
                details={"symbol": symbol, "interval": "15m"},
            )
            candles = self._fetcher.fetch_klines(symbol, "15m")
            self._logger.info(
                "Fetched candles",
                details={"symbol": symbol, "count": len(candles)},
            )
            indicators = self._indicator_calc.calculate(candles[-50:])
            if not indicators:
                self._logger.warning(
                    "Indicator calculation returned no values",
                    details={"symbol": symbol},
                )
                continue
            latest_indicator = indicators[-1]
            signals = self._signal_eval.evaluate([latest_indicator])
            latest_signal = signals[-1] if signals else None
            self._context_builder.update_market_snapshot(latest_indicator, latest_signal)
            if latest_signal:
                self._logger.log_signal(latest_signal)
                candidates.append(latest_signal)
            else:
                self._logger.info(
                    "No tradable signal for symbol",
                    details={"symbol": symbol},
                )

        best = self._select_best_signal(candidates)
        if not best or best.direction == TradeDirection.FLAT:
            self._logger.info(
                "No actionable signal selected",
                details={"candidates": len(candidates)},
            )
            return

        # Placeholder for price, in production use last close or order book mid.
        entry_price = self._estimate_entry_price(best)
        volatility = self._extract_volatility(best)
        self._logger.info(
            "Planning position",
            details={
                "symbol": best.symbol,
                "direction": best.direction.value,
                "confidence": f"{best.confidence:.3f}",
            },
        )
        position = self._order_planner.create_position(
            best, account_equity=10_000, price=entry_price, volatility=volatility
        )
        self._state_machine.enter_position(position)
        self._logger.success(
            "Position planned",
            details={
                "symbol": position.symbol,
                "size": f"{position.size:.4f}",
                "entry_price": f"{position.entry_price:.2f}",
            },
        )
        self._logger.log_position(position)

    def run_minute_review(self) -> None:
        """1m job: let DeepSeek review current position and decide actions."""
        now = datetime.now(tz=timezone.utc)
        self._logger.info(
            "Starting minute review",
            details={"timestamp": now.isoformat()},
        )
        if not self._state_machine.needs_minute_review(now):
            self._logger.info(
                "Minute review skipped",
                details={"reason": "cooldown"},
            )
            return

        position = self._state_machine.state.current_position
        if position is None:
            self._state_machine.mark_minute_review(now)
            self._logger.info("No open position for review")
            return

        payload = self._context_builder.build_ai_payload(position)
        self._logger.info(
            "Requesting AI evaluation",
            details={"symbol": position.symbol, "size": f"{position.size:.4f}"},
        )
        evaluation = self._ai_client.evaluate(payload)
        self._logger.log_ai(evaluation)
        self._logger.info(
            "AI review completed",
            details={"action": evaluation.action, "confidence": f"{evaluation.confidence:.2f}"},
        )

        if evaluation.action in {"close", "take_profit", "stop_loss"}:
            self._state_machine.exit_position()
            self._logger.warning(
                "Position exit triggered",
                details={"action": evaluation.action},
            )
        self._state_machine.mark_minute_review(now)

    def _select_best_signal(self, signals: List[Signal]) -> Optional[Signal]:
        signals = [s for s in signals if s.direction != TradeDirection.FLAT]
        if not signals:
            return None
        return max(signals, key=lambda s: s.confidence)

    def _estimate_entry_price(self, signal: Signal) -> float:
        """This method should be replaced with live pricing integration."""
        return 100.0

    def _extract_volatility(self, signal: Signal) -> Optional[float]:
        atr_value = signal.metadata.get("atr")
        if isinstance(atr_value, (int, float)) and atr_value > 0:
            return float(atr_value)
        return None

    def shutdown(self) -> None:
        self._logger.info("Shutting down services")
        self._fetcher.close()
        self._ai_client.close()
