from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

import pandas as pd

from trading_bot.data.models import FeatureBundle, IndicatorSnapshot, MarketSnapshot


@dataclass(slots=True)
class IndicatorEngine:
    ma_windows: Sequence[int] = (20, 50)
    ema_windows: Sequence[int] = (12, 26)
    rsi_period: int = 14

    def build_bundle(
        self, symbol: str, snapshots: Sequence[MarketSnapshot]
    ) -> FeatureBundle:
        indicators: Dict[str, IndicatorSnapshot] = {}
        for snap in snapshots:
            indicators[snap.timeframe] = IndicatorSnapshot(
                timeframe=snap.timeframe,
                values=self._compute_for_snapshot(snap),
            )
        return FeatureBundle(symbol=symbol, created_at=snapshots[0].latest().timestamp, indicators=indicators)

    def _compute_for_snapshot(self, snapshot: MarketSnapshot) -> Dict[str, float]:
        df = pd.DataFrame(
            [
                {
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "vwap": candle.vwap or candle.close,
                }
                for candle in snapshot.candles
            ]
        ).set_index("timestamp")

        values: Dict[str, float] = {}
        for window in self.ma_windows:
            values[f"ma_{window}"] = df["close"].rolling(window).mean().iloc[-1]
        for window in self.ema_windows:
            values[f"ema_{window}"] = df["close"].ewm(span=window, adjust=False).mean().iloc[-1]

        ema_fast = df["close"].ewm(span=12, adjust=False).mean()
        ema_slow = df["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        values["macd"] = macd_line.iloc[-1]
        values["macd_signal"] = signal_line.iloc[-1]
        values["macd_hist"] = macd_hist.iloc[-1]

        rsi = self._rsi(df["close"], self.rsi_period)
        values["rsi"] = rsi.iloc[-1]

        values["close"] = df["close"].iloc[-1]
        values["avg_price"] = df["vwap"].iloc[-1]
        values["volume"] = df["volume"].iloc[-1]
        values["range_pct"] = (df["high"].iloc[-1] - df["low"].iloc[-1]) / df["close"].iloc[-1]
        return values

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100 - (100 / (1 + rs))
