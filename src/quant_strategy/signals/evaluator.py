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
             direction, confidence, reason = self._score_indicator(indicator)
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
                     },
                 )
             )
         return signals

     def _score_indicator(self, indicator: IndicatorSet) -> tuple[TradeDirection, float, str]:
         macd_hist = indicator.macd.get("hist", 0.0)
         macd_signal = indicator.macd.get("signal", 0.0)
         ma_fast = indicator.ma.get(5, 0.0)
         ma_slow = indicator.ma.get(20, 0.0)
         rsi_short = indicator.rsi.get(6, 50.0)
         volume_ratio = indicator.volume_ratio or 1.0

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

         direction = TradeDirection.FLAT
         if score > 0.1:
             direction = TradeDirection.LONG
         elif score < -0.1:
             direction = TradeDirection.SHORT

         confidence = self._map_score_to_confidence(abs(score))
         reason_text = "；".join(reasons) if reasons else "信号弱"
         return direction, confidence, reason_text

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
