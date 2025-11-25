"""High-level orchestration tasks for cron/minutely runners."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from quant_strategy.ai.deepseek_client import DeepSeekClient
from quant_strategy.core.config import Config
from quant_strategy.core.models import IndicatorSet, Signal, TradeDirection
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
        """Data job: pull multi-interval candles, fuse signals, plan orders."""
        candidates: List[Signal] = []
        for symbol in self._config.data.symbols:
            signal = self._generate_signal_for_symbol(symbol)
            if not signal:
                continue
            self._logger.log_signal(signal)
            if signal.direction != TradeDirection.FLAT:
                candidates.append(signal)
        best = self._select_best_signal(candidates)
        if not best or best.direction == TradeDirection.FLAT:
            return

        # Use the freshest cached close; production may swap in live order book mid.
        indicator = self._context_builder.get_latest_indicator(best.symbol)
        entry_price = self._estimate_entry_price(best, indicator)
        volatility = self._extract_volatility(best, indicator)
        position = self._order_planner.create_position(
            best, account_equity=10_000, price=entry_price, volatility=volatility
        )
        self._state_machine.enter_position(position)
        self._logger.log_position(position)

    def run_minute_review(self) -> None:
        """1m job: let DeepSeek review current position and decide actions."""
        now = datetime.now(tz=timezone.utc)
        if not self._state_machine.needs_minute_review(now):
            return

        position = self._state_machine.state.current_position
        if position is None:
            self._state_machine.mark_minute_review(now)
            return

        minutes_to_close = self._minutes_until_session_close(now)
        force_close, reason = self._state_machine.should_force_close(now, minutes_to_close)
        if force_close:
            self._logger.log_force_close(position.symbol, reason or "强平规则触发")
            self._state_machine.exit_position()
            self._state_machine.mark_minute_review(now)
            return

        payload = self._context_builder.build_ai_payload(position)
        evaluation = self._ai_client.evaluate(payload)
        self._logger.log_ai(evaluation)

        if evaluation.action in {"close", "take_profit", "stop_loss"}:
            self._state_machine.exit_position()
        self._state_machine.mark_minute_review(now)

    def _generate_signal_for_symbol(self, symbol: str) -> Signal | None:
        intervals = self._config.data.intervals or ["15m"]
        interval_results: Dict[str, Tuple[IndicatorSet, Signal]] = {}
        for interval in intervals:
            indicator = self._fetch_latest_indicator(symbol, interval)
            if indicator is None:
                continue
            signals = self._signal_eval.evaluate([indicator])
            if not signals:
                continue
            interval_results[interval] = (indicator, signals[-1])

        if not interval_results:
            return None

        base_interval = intervals[0] if intervals else next(iter(interval_results.keys()))
        if base_interval not in interval_results:
            base_interval = next(iter(interval_results.keys()))
        base_indicator, base_signal = interval_results[base_interval]

        fused_signal = self._fuse_signals(base_signal, interval_results, base_interval)
        self._context_builder.update_market_snapshot(base_indicator, fused_signal)
        return fused_signal

    def _fetch_latest_indicator(self, symbol: str, interval: str) -> IndicatorSet | None:
        candles = self._fetcher.fetch_klines(symbol, interval)
        if not candles:
            return None
        recent = candles[-200:] if len(candles) > 200 else candles
        indicators = self._indicator_calc.calculate(recent)
        if not indicators:
            return None
        return indicators[-1]

    def _fuse_signals(
        self,
        base_signal: Signal,
        interval_signals: Dict[str, Tuple[IndicatorSet, Signal]],
        base_interval: str,
    ) -> Signal:
        confirmations: List[str] = []
        conflicts: List[str] = []
        for interval, (_, signal) in interval_signals.items():
            if interval == base_interval or signal.direction == TradeDirection.FLAT:
                continue
            if signal.direction == base_signal.direction and base_signal.direction != TradeDirection.FLAT:
                confirmations.append(interval)
            elif base_signal.direction != TradeDirection.FLAT:
                conflicts.append(f"{interval}:{signal.direction.value}")

        reason_parts = [base_signal.reason]
        metadata = dict(base_signal.metadata)
        metadata["base_interval"] = base_interval
        metadata["interval_breakdown"] = {
            interval: sig.direction.value for interval, (_, sig) in interval_signals.items()
        }
        max_conf = self._config.risk.confidence_buckets[-1]
        min_conf = self._config.risk.confidence_buckets[0]

        if conflicts:
            reason_parts.append("高周期方向冲突")
            return Signal(
                symbol=base_signal.symbol,
                direction=TradeDirection.FLAT,
                confidence=min_conf,
                reason="；".join(reason_parts),
                timestamp=base_signal.timestamp,
                metadata={**metadata, "conflicts": conflicts},
            )

        confidence = base_signal.confidence
        if confirmations and base_signal.direction != TradeDirection.FLAT:
            bonus = 0.05 * len(confirmations)
            confidence = min(confidence + bonus, max_conf)
            reason_parts.append(f"{'/'.join(confirmations)} 同向确认")

        return Signal(
            symbol=base_signal.symbol,
            direction=base_signal.direction,
            confidence=confidence,
            reason="；".join(reason_parts),
            timestamp=base_signal.timestamp,
            metadata={**metadata, "confirmations": confirmations},
        )

    def _select_best_signal(self, signals: List[Signal]) -> Signal | None:
        signals = [s for s in signals if s.direction != TradeDirection.FLAT]
        if not signals:
            return None
        return max(signals, key=lambda s: s.confidence)

    def _minutes_until_session_close(self, now: datetime) -> int:
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delta = tomorrow - now
        return max(int(delta.total_seconds() // 60), 0)

    def _estimate_entry_price(self, signal: Signal, indicator: IndicatorSet | None) -> float:
        if indicator and indicator.close:
            return indicator.close
        close = signal.metadata.get("close")
        if isinstance(close, (int, float)) and close > 0:
            return float(close)
        return 100.0

    def _extract_volatility(self, signal: Signal, indicator: IndicatorSet | None) -> float | None:
        atr_value = indicator.atr if indicator else None
        if isinstance(atr_value, (int, float)) and atr_value > 0:
            return float(atr_value)
        fallback = signal.metadata.get("atr")
        if isinstance(fallback, (int, float)) and fallback > 0:
            return float(fallback)
        return None

    def shutdown(self) -> None:
        self._fetcher.close()
        self._ai_client.close()
