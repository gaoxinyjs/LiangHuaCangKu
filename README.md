# DeepSeek AI Trading Orchestrator

本项目提供一个模块化、可扩展的量化交易执行框架，将行情采集、指标计算、DeepSeek 信号推理、策略决策、执行风控和调度监控全面解耦，便于后续替换真实交易所与模型接口。

## 功能概览

- **多周期行情拉取**：按配置同步 15m / 1h / 4h / 1d K 线与成交量。
- **指标引擎**：计算 MA、EMA、MACD、RSI、量价信息以及波动率指标。
- **DeepSeek AI 模块**：封装成 `AISignalProvider`，当前内置随机 Stub，便于后续接入真实推理服务。
- **策略模块**：`DeepSeekHybridStrategy` 结合指标趋势、RSI、AI 置信度与支撑/阻力信息，生成开平仓意图，同时按置信度映射五档仓位。
- **执行与风控**：`PortfolioExecutor` 负责“有仓先平”的规则、止盈止损、强制平仓判定以及盈亏统计。
- **调度器**：`TradingOrchestrator` 将 15 分钟行情循环与每分钟仓位巡检完全拆分，满足“开仓→每分钟复核→最后 15 分钟强平”的要求。

## 快速开始

```bash
pip install -e .
python -m trading_bot.main --minutes 0.2
```

默认使用 `MockMarketDataProvider` 与 `DeepSeekStub` 生成随机行情/信号，用于演示模块串联流程。接入真实交易所与 DeepSeek 服务时，只需实现对应接口并在 `main.py` 中注入即可。

## 目录结构

- `trading_bot/config`：集中管理全局参数（时间周期、仓位档位、调度节奏等）。
- `trading_bot/data`：行情模型与数据提供者接口，内含系统时间与 Mock Provider 示例。
- `trading_bot/indicators`：指标计算引擎，产出 `FeatureBundle` 给 AI 与策略使用。
- `trading_bot/ai`：AI 信号模型与 DeepSeek Stub。
- `trading_bot/strategy`：策略接口、上下文与混合策略实现。
- `trading_bot/execution`：仓位对象与执行器，处理开平仓、止盈止损和强制平仓。
- `trading_bot/scheduler`：协程调度器，驱动 15 分钟行情循环与每分钟仓位巡检。
- `trading_bot/main.py`：程序入口，可通过参数控制演示运行时长。

## 下一步

1. 将 `MockMarketDataProvider` 替换为交易所 REST/WebSocket 实现，确保多周期同步。
2. 接入真实 DeepSeek 推理接口（可通过 HTTP/WS 调用）并添加模型限流。
3. 在 `PortfolioExecutor` 中对接交易所下单/撤单 API，并补充手续费与滑点建模。
4. 扩展调度器，加入回测模式、指标回溯缓存以及监控告警输出。
