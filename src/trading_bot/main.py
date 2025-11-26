from __future__ import annotations

import argparse
import asyncio
import logging

from trading_bot.ai.deepseek_stub import DeepSeekStub
from trading_bot.config.models import AppConfig, default_config
from trading_bot.data.providers import MockMarketDataProvider, SystemTimeProvider
from trading_bot.execution.executor import PortfolioExecutor
from trading_bot.indicators.engine import IndicatorEngine
from trading_bot.scheduler.orchestrator import TradingOrchestrator
from trading_bot.strategy.rule_strategy import DeepSeekHybridStrategy


async def run_app(config: AppConfig, run_minutes: float) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    time_provider = SystemTimeProvider()
    data_provider = MockMarketDataProvider(time_provider=time_provider)
    indicator_engine = IndicatorEngine()
    ai_provider = DeepSeekStub()
    strategy = DeepSeekHybridStrategy(config)
    executor = PortfolioExecutor(config)
    orchestrator = TradingOrchestrator(
        config=config,
        data_provider=data_provider,
        indicator_engine=indicator_engine,
        ai_provider=ai_provider,
        strategy=strategy,
        executor=executor,
        time_provider=time_provider,
    )

    await orchestrator.start()
    try:
        await asyncio.sleep(run_minutes * 60)
    finally:
        await orchestrator.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DeepSeek AI trading orchestrator")
    parser.add_argument(
        "--minutes",
        type=float,
        default=1.0,
        help="Run duration in minutes for demo purposes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = default_config()
    asyncio.run(run_app(config, run_minutes=args.minutes))


if __name__ == "__main__":
    main()
