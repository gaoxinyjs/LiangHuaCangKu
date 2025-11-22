 """Configuration loading utilities for the strategy framework."""

 from __future__ import annotations

 from pathlib import Path
 from typing import List

 import yaml
 from pydantic import BaseModel, Field


 class ExchangeConfig(BaseModel):
     name: str = "binance"
     base_url: str = "https://api.binance.com"
     ws_url: str = "wss://stream.binance.com:9443/ws"
     api_key: str | None = None
     api_secret: str | None = None
     rate_limit_per_minute: int = 1200
     fallback_exchanges: List[str] = Field(default_factory=list)


 class DataConfig(BaseModel):
     symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
     intervals: List[str] = Field(default_factory=lambda: ["15m", "4h", "1d"])
     refresh_seconds: int = 900  # 15 minutes
     cache_ttl_seconds: int = 600
     history_limit: int = 500


 class IndicatorConfig(BaseModel):
     macd_fast: int = 12
     macd_slow: int = 26
     macd_signal: int = 9
     ma_windows: List[int] = Field(default_factory=lambda: [5, 20, 60])
     ema_windows: List[int] = Field(default_factory=lambda: [12, 26])
     rsi_windows: List[int] = Field(default_factory=lambda: [6, 14])


 class AiConfig(BaseModel):
     provider: str = "deepseek"
     api_url: str = "https://api.deepseek.com/v1/chat/completions"
     api_key: str | None = None
     model: str = "deepseek-trader"
     timeout_seconds: int = 15
     retry_attempts: int = 3


 class RiskConfig(BaseModel):
     leverage: float = 5.0
     take_profit_pct: float = 0.06
     stop_loss_pct: float = 0.03
     confidence_buckets: List[float] = Field(default_factory=lambda: [0.05, 0.08, 0.10, 0.12, 0.15])
     max_position_minutes: int = 120
     forced_close_minutes_before_eod: int = 15


 class SchedulerConfig(BaseModel):
     minute_review_interval: int = 60
     data_pull_interval: int = 900


 class Config(BaseModel):
     exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
     data: DataConfig = Field(default_factory=DataConfig)
     indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
     ai: AiConfig = Field(default_factory=AiConfig)
     risk: RiskConfig = Field(default_factory=RiskConfig)
     scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)

     @staticmethod
     def load(path: str | Path | None = None) -> "Config":
         """Load config from YAML file if provided, otherwise use defaults."""
         if path is None:
             return Config()
         data = yaml.safe_load(Path(path).read_text())
         return Config(**data)
