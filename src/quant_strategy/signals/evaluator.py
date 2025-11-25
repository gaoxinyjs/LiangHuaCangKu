"""Signal generation module that fuses indicators and heuristics."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from quant_strategy.core.config import RiskConfig
from quant_strategy.core.models import IndicatorSet, Signal, TradeDirection


class SignalEvaluator:
    """Generate directional signals and confidence scores."""

    def __init__(self, risk_cfg: RiskConfig) -> None:
        self._risk = risk_cfg

    def evaluate(self, indicators: List[IndicatorSet]) -> List[Signal]:
        signals: List[Signal] = []
        for indicator in indicators:
            direction, confidence, reason, raw_score = self._score_indicator(indicator)
            volatility_pct = 0.0
            if indicator.atr and indicator.close:
                volatility_pct = indicator.atr / max(indicator.close, 1e-9)
            signals.append(
                Signal(
                    symbol=indicator.symbol,
                    direction=direction,
                    confidence=confidence,
                    reason=reason,
                    timestamp=indicator.timestamp,
                    metadata={
                        "macd_hist": indicator.macd.get("hist", 0.0),
                        "volume_ratio": indicator.volume_ratio or 0.0,
                        "atr": indicator.atr or 0.0,
                        "score": raw_score,
                        "volatility_pct": volatility_pct,
                        "close": indicator.close,
                        "interval": indicator.interval,
                    },
                )
            )
        return signals

    def _score_indicator(self, indicator: IndicatorSet) -> tuple[TradeDirection, float, str, float]:
        macd_hist = indicator.macd.get("hist", 0.0)
        macd_signal = indicator.macd.get("signal", 0.0)
        ma_fast = indicator.ma.get(5, 0.0)
        ma_slow = indicator.ma.get(20, 0.0)
        ma_long = indicator.ma.get(60, ma_slow)
        ema_fast = indicator.ema.get(12, ma_fast)
        ema_slow = indicator.ema.get(26, ma_slow)
        rsi_short = indicator.rsi.get(6, 50.0)
        volume_ratio = indicator.volume_ratio or 1.0
        price = indicator.close

        score = 0.0
        reasons: List[str] = []

        if macd_hist > 0 and macd_hist > macd_signal:
            score += 0.3
            reasons.append("MACD 多头动能增强")
        elif macd_hist < 0 and macd_hist < macd_signal:
            score -= 0.3
            reasons.append("MACD 空头动能增强")

        if ma_fast > ma_slow:
            score += 0.2
            reasons.append("均线金叉")
        elif ma_fast < ma_slow:
            score -= 0.2
            reasons.append("均线死叉")

        if ema_fast > ema_slow:
            score += 0.1
            reasons.append("EMA 多头趋势")
        elif ema_fast < ema_slow:
            score -= 0.1
            reasons.append("EMA 空头趋势")

        if price and ma_long:
            if price > ma_long:
                score += 0.05
                reasons.append("价格站上长周期均线")
            elif price < ma_long:
                score -= 0.05
                reasons.append("价格跌破长周期均线")

        if rsi_short > 65:
            score -= 0.1
            reasons.append("RSI 超买")
        elif rsi_short < 35:
            score += 0.1
            reasons.append("RSI 超卖")

        if volume_ratio > 1.5:
            score += 0.1
            reasons.append("放量")
        elif volume_ratio < 0.7:
            score -= 0.05
            reasons.append("缩量")

        atr = indicator.atr or 0.0
        if atr and price:
            volatility_pct = atr / max(price, 1e-9)
            if volatility_pct > 0.03:
                score -= 0.05
                reasons.append("波动加剧")
            elif volatility_pct < 0.015:
                score += 0.05
                reasons.append("波动收敛")

        direction = TradeDirection.FLAT
        if score > 0.1:
            direction = TradeDirection.LONG
        elif score < -0.1:
            direction = TradeDirection.SHORT

        confidence = self._map_score_to_confidence(abs(score))
        reason_text = "；".join(reasons) if reasons else "信号弱"
        return direction, confidence, reason_text, score

    def _map_score_to_confidence(self, score: float) -> float:
        """Map raw score 0-1 to configured confidence buckets."""
        buckets = self._risk.confidence_buckets
        if score < 0.2:
            return buckets[0]
        if score < 0.4:
            return buckets[1]
        if score < 0.6:
            return buckets[2]
        if score < 0.8:
            return buckets[3]
        return buckets[4]
