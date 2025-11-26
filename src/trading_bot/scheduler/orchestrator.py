from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Iterable, Sequence

from trading_bot.ai.base import AISignalProvider
from trading_bot.config.models import AppConfig, TimeframeConfig
from trading_bot.data.models import MarketSnapshot
from trading_bot.data.provider_base import MarketDataProvider, TimeProvider
from trading_bot.execution.executor import ExecutionReport, PortfolioExecutor
from trading_bot.indicators.engine import IndicatorEngine
from trading_bot.strategy.base import TradingStrategy
from trading_bot.strategy.models import StrategyContext, TradeIntent

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        data_provider: MarketDataProvider,
        indicator_engine: IndicatorEngine,
        ai_provider: AISignalProvider,
        strategy: TradingStrategy,
        executor: PortfolioExecutor,
        time_provider: TimeProvider,
    ) -> None:
        self._config = config
        self._data_provider = data_provider
        self._indicator_engine = indicator_engine
        self._ai_provider = ai_provider
        self._strategy = strategy
        self._executor = executor
        self._time = time_provider
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._data_cycle_loop(), name="data-cycle"),
            asyncio.create_task(self._position_loop(), name="position-loop"),
        ]

    async def run_forever(self) -> None:
        await self.start()
        await self.wait_until_stopped()

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        finally:
            self._tasks.clear()

    async def wait_until_stopped(self) -> None:
        if not self._tasks:
            return
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    async def _data_cycle_loop(self) -> None:
        interval = self._config.scheduling.data_pull_minutes * 60
        while self._running:
            try:
                await self.evaluate_market_cycle()
            except Exception as exc:
                logger.exception("Data cycle failed: %s", exc)
            await asyncio.sleep(interval)

    async def _position_loop(self) -> None:
        interval = self._config.scheduling.position_poll_seconds
        while self._running:
            try:
                await self.evaluate_active_position()
            except Exception as exc:
                logger.exception("Position loop failed: %s", exc)
            await asyncio.sleep(interval)

    async def evaluate_market_cycle(self) -> ExecutionReport | None:
        snapshots = await self._fetch_all_timeframes(self._config.data.timeframes)
        bundle = self._indicator_engine.build_bundle(self._config.data.symbol, snapshots)
        ai_signal = await self._ai_provider.infer(bundle)
        mark_price = snapshots[0].latest().close
        context = StrategyContext(
            config=self._config,
            features=bundle,
            ai_signal=ai_signal,
            active_position=self._executor.position,
            mark_price=mark_price,
        )
        intent = self._strategy.decide(context)
        report = self._executor.execute(intent, timestamp=self._time.now())
        if report.action != "hold":
            logger.info("Execution: %s | %s", report.action, report.message)
        return report

    async def evaluate_active_position(self) -> ExecutionReport | None:
        position = self._executor.position
        if not position:
            return None

        short_tf = self._config.data.timeframes[0]
        snapshots = await self._fetch_all_timeframes((short_tf,))
        bundle = self._indicator_engine.build_bundle(self._config.data.symbol, snapshots)
        ai_signal = await self._ai_provider.infer(bundle)
        mark_price = snapshots[0].latest().close

        if self._executor.needs_force_close(self._time.now()):
            intent = TradeIntent(
                action="close",
                entry_price=mark_price,
                reason="Force close window",
            )
            return self._executor.execute(intent, timestamp=self._time.now())

        context = StrategyContext(
            config=self._config,
            features=bundle,
            ai_signal=ai_signal,
            active_position=position,
            mark_price=mark_price,
        )
        intent = self._strategy.decide(context)
        if intent.action == "close":
            intent.entry_price = mark_price
        report = self._executor.execute(intent, timestamp=self._time.now())
        if report.action != "hold":
            logger.info("Position monitor: %s | %s", report.action, report.message)
        return report

    async def _fetch_all_timeframes(
        self, timeframes: Sequence[TimeframeConfig]
    ) -> list[MarketSnapshot]:
        results: list[MarketSnapshot] = []
        for tf in timeframes:
            snapshot = await self._data_provider.fetch_snapshot(
                symbol=self._config.data.symbol,
                timeframe=tf.label,
                lookback=tf.lookback,
            )
            results.append(snapshot)
        return results
