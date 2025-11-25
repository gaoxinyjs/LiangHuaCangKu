 """Wrapper for DeepSeek (or similar) LLM evaluation."""

 from __future__ import annotations

 import json
 from typing import Any, Dict

 import httpx
 from tenacity import Retrying, stop_after_attempt, wait_fixed

 from quant_strategy.core.config import AiConfig
 from quant_strategy.core.models import AiEvaluation


 class DeepSeekClient:
     """Call DeepSeek chat endpoint with structured prompts."""

     def __init__(self, config: AiConfig) -> None:
         self._cfg = config
         self._client = httpx.Client(timeout=config.timeout_seconds)

     def evaluate(self, payload: Dict[str, Any]) -> AiEvaluation:
         headers = {"Authorization": f"Bearer {self._cfg.api_key}"} if self._cfg.api_key else {}
         request_body = {
             "model": self._cfg.model,
             "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a disciplined crypto swing-trading assistant. "
                        "Respond only in JSON with fields action (hold|close|take_profit|stop_loss), "
                        "reason, risk_level, confidence (0-1). "
                        "Ground every decision in the supplied market_snapshot, latest_signal, "
                        "position stats, and risk_constraints."
                    ),
                },
                 {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
             ],
             "response_format": {"type": "json_object"},
         }

         for attempt in self._retrying():
             with attempt:
                 response = self._client.post(self._cfg.api_url, headers=headers, json=request_body)
                 response.raise_for_status()
                 data = response.json()
                 content = data["choices"][0]["message"]["content"]
                 parsed = json.loads(content)
                 return AiEvaluation(
                     action=parsed.get("action", "hold"),
                     reason=parsed.get("reason", ""),
                     risk_level=parsed.get("risk_level", "medium"),
                     confidence=float(parsed.get("confidence", 0.5)),
                     raw_response=data,
                 )
         raise RuntimeError("DeepSeek evaluation retries exhausted")

     def close(self) -> None:
         self._client.close()

     def _retrying(self) -> Retrying:
         return Retrying(
             wait=wait_fixed(2),
             stop=stop_after_attempt(self._cfg.retry_attempts),
             reraise=True,
         )
