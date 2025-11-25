"""Entry point for manual runs or schedulers."""

from __future__ import annotations

import argparse
from contextlib import suppress

from quant_strategy.core.config import Config
from quant_strategy.scheduler.tasks import StrategyTasks


def cli() -> None:
    parser = argparse.ArgumentParser(description="Quant strategy orchestrator")
    parser.add_argument("--config", type=str, help="Path to YAML config", default=None)
    parser.add_argument("--task", type=str, choices=["data", "minute"], default="data")
    args = parser.parse_args()

    cfg = Config.load(args.config)
    tasks = StrategyTasks(cfg)
    try:
        if args.task == "data":
            tasks.run_data_cycle()
        else:
            tasks.run_minute_review()
    finally:
        with suppress(Exception):
            tasks.shutdown()


if __name__ == "__main__":
    cli()
