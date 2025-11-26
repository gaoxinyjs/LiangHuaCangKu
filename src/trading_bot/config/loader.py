from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from trading_bot.config.models import (
    AppConfig,
    DataConfig,
    RiskConfig,
    SchedulingConfig,
    StrategyToggles,
    TimeframeConfig,
    default_config,
)

try:  # pragma: no cover - python < 3.11 fallback
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[assignment]


CONFIG_ENV_PREFIX = "BOT_"


def load_config(path: str | None = None, env_prefix: str = CONFIG_ENV_PREFIX) -> AppConfig:
    config = default_config()
    if path:
        payload = _read_file(Path(path))
        config = AppConfig(
            data=_merge_data_config(config.data, payload.get("data")),
            risk=_merge_risk_config(config.risk, payload.get("risk")),
            scheduling=_merge_sched_config(config.scheduling, payload.get("scheduling")),
            toggles=_merge_toggle_config(config.toggles, payload.get("toggles")),
            metadata=payload.get("metadata", config.metadata),
        )
    return _apply_env_overrides(config, env_prefix=env_prefix)


def _read_file(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".toml", ".tml"}:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    raise ValueError(f"Unsupported config format: {path.suffix}")


def _merge_data_config(base: DataConfig, payload: Mapping[str, Any] | None) -> DataConfig:
    if not payload:
        return base
    updates: dict[str, Any] = {}
    if "symbol" in payload:
        updates["symbol"] = payload["symbol"]
    if "timeframes" in payload:
        updates["timeframes"] = tuple(
            TimeframeConfig(**tf) if not isinstance(tf, TimeframeConfig) else tf
            for tf in payload["timeframes"]
        )
    return replace(base, **updates) if updates else base


def _merge_risk_config(base: RiskConfig, payload: Mapping[str, Any] | None) -> RiskConfig:
    if not payload:
        return base
    return replace(base, **payload)


def _merge_sched_config(
    base: SchedulingConfig, payload: Mapping[str, Any] | None
) -> SchedulingConfig:
    if not payload:
        return base
    return replace(base, **payload)


def _merge_toggle_config(
    base: StrategyToggles, payload: Mapping[str, Any] | None
) -> StrategyToggles:
    if not payload:
        return base
    return replace(base, **payload)


def _apply_env_overrides(config: AppConfig, env_prefix: str) -> AppConfig:
    symbol = os.getenv(f"{env_prefix}SYMBOL")
    leverage = _get_env_float(f"{env_prefix}LEVERAGE")
    take_profit = _get_env_float(f"{env_prefix}TAKE_PROFIT")
    stop_loss = _get_env_float(f"{env_prefix}STOP_LOSS")

    data_cfg = config.data
    risk_cfg = config.risk

    if symbol:
        data_cfg = replace(data_cfg, symbol=symbol)
    risk_updates: dict[str, Any] = {}
    if leverage is not None:
        risk_updates["leverage"] = leverage
    if take_profit is not None:
        risk_updates["take_profit_pct"] = take_profit
    if stop_loss is not None:
        risk_updates["stop_loss_pct"] = stop_loss
    if risk_updates:
        risk_cfg = replace(risk_cfg, **risk_updates)

    return AppConfig(
        data=data_cfg,
        risk=risk_cfg,
        scheduling=config.scheduling,
        toggles=config.toggles,
        metadata=config.metadata,
    )


def _get_env_float(key: str) -> float | None:
    raw = os.getenv(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
