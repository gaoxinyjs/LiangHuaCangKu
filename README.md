# 模块化量化策略框架

该项目实现了一个面向 DeepSeek 辅助决策的加密策略骨架，覆盖“拉取数据 → 指标/信号 → 下单执行 → 每分钟 AI 复评 → 强制平仓”的完整链路。整体采用模块化设计，便于后续扩展。

## 目录结构

- `src/quant_strategy/core`: 基础配置与共享数据模型。
- `src/quant_strategy/data`: 行情抓取（含重试/限频预留）。
- `src/quant_strategy/indicators`: 基于 Pandas 的 MACD/MA/EMA/RSI 计算。
- `src/quant_strategy/signals`: 量价融合的信号打分与信心映射。
- `src/quant_strategy/ai`: DeepSeek API 包装器，返回结构化评估。
- `src/quant_strategy/execution`: 仓位 sizing、止盈止损计算、状态机。
- `src/quant_strategy/monitoring`: Rich 表格输出，便于调试监控。
- `src/quant_strategy/scheduler`: 15 分钟数据任务与 1 分钟复评任务。
- `src/quant_strategy/main.py`: CLI 入口，可通过 `--task data/minute` 触发不同任务。

## 快速开始

```bash
pip install -e .
export DEEPSEEK_API_KEY=xxx  # 写入 config.yaml 亦可
python -m quant_strategy.main --task data
python -m quant_strategy.main --task minute
```

自定义配置可参考 `core/config.py` 中的字段说明，保存为 YAML 后用 `--config path/to/config.yaml` 载入。

## 后续扩展方向

1. 接入真实交易所订单接口与 Websocket 订阅，完善持仓监听。
2. 将策略状态持久化到数据库/Redis，支持多进程/多实例调度。
3. 在回测/模拟盘环境验证策略，再逐步放量真实资金。
4. 增加监控/告警（Prometheus/Grafana）与审计日志，提升可观测与风控能力。
