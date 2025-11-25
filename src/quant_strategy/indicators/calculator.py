 """Indicator calculation helpers built on top of pandas."""

 from __future__ import annotations

 import pandas as pd

 from quant_strategy.core.config import IndicatorConfig
 from quant_strategy.core.models import IndicatorSet, OHLCV


 class IndicatorCalculator:
     """Calculate MA/EMA/MACD/RSI and volume ratios on OHLCV series."""

     def __init__(self, config: IndicatorConfig) -> None:
         self._cfg = config

     def calculate(self, candles: list[OHLCV]) -> list[IndicatorSet]:
         if not candles:
             return []

        df = pd.DataFrame(
            {
                "timestamp": [c.open_time for c in candles],
                "close": [c.close for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "volume": [c.volume for c in candles],
            }
        ).set_index("timestamp")

        ma = {window: df["close"].rolling(window).mean() for window in self._cfg.ma_windows}
        ema = {window: df["close"].ewm(span=window, adjust=False).mean() for window in self._cfg.ema_windows}

        fast = df["close"].ewm(span=self._cfg.macd_fast, adjust=False).mean()
        slow = df["close"].ewm(span=self._cfg.macd_slow, adjust=False).mean()
        macd_line = fast - slow
        signal = macd_line.ewm(span=self._cfg.macd_signal, adjust=False).mean()
        hist = macd_line - signal

        def _rsi(series: pd.Series, window: int) -> pd.Series:
            delta = series.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
            loss = -delta.clip(upper=0).ewm(alpha=1 / window, adjust=False).mean()
            rs = gain / (loss + 1e-9)
            return 100 - (100 / (1 + rs))

        rsi = {window: _rsi(df["close"], window) for window in self._cfg.rsi_windows}

        volume_ratio = df["volume"] / df["volume"].rolling(20).mean()
        prev_close = df["close"].shift(1)
        true_range = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = true_range.ewm(alpha=1 / max(self._cfg.atr_window, 1), adjust=False).mean()

        out: list[IndicatorSet] = []
        for candle in candles:
            timestamp = candle.open_time
            atr_value = atr.get(timestamp)
            out.append(
                IndicatorSet(
                    symbol=candle.symbol,
                    interval=candle.interval,
                    timestamp=timestamp,
                    close=candle.close,
                    volume=candle.volume,
                    atr=float(atr_value) if pd.notna(atr_value) else None,
                    ma={window: ma_series.get(timestamp, float("nan")) for window, ma_series in ma.items()},
                    ema={window: ema_series.get(timestamp, float("nan")) for window, ema_series in ema.items()},
                    macd={
                        "line": macd_line.get(timestamp, float("nan")),
                        "signal": signal.get(timestamp, float("nan")),
                        "hist": hist.get(timestamp, float("nan")),
                    },
                    rsi={window: rsi_series.get(timestamp, float("nan")) for window, rsi_series in rsi.items()},
                    volume_ratio=float(volume_ratio.get(timestamp, float("nan"))),
                )
            )
        return out
