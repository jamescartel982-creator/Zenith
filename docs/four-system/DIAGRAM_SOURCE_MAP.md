# Every supplied TradingAgents diagram component

All 20 nodes are mapped; labelled files are corrected to the actual pinned tree. The user is an actor, owned by the CLI entry rather than a separate implementation.

| Diagram label | Exact source |
|---|---|
| Analyst user | [cli/main.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/cli/main.py#L1) |
| CLI commands | [cli/main.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/cli/main.py#L1) |
| Run orchestration | [cli/run.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/cli/run.py#L1) |
| Backtesting | [tradingagents/backtest.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/backtest.py#L1) |
| Trading graph | [tradingagents/graph/trading_graph.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/graph/trading_graph.py#L1) |
| Analyst team | [tradingagents/graph/setup.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/graph/setup.py#L1) |
| Prompt context | [tradingagents/agents/context.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/context.py#L1) |
| Bull-bear debate | [tradingagents/agents/researchers/bull_researcher.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/researchers/bull_researcher.py#L1) |
| Research manager | [tradingagents/agents/managers/research_manager.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/managers/research_manager.py#L1) |
| Trader | [tradingagents/agents/trader/trader.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/trader/trader.py#L1) |
| Risk debate | [tradingagents/agents/risk_mgmt/aggressive_debator.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/risk_mgmt/aggressive_debator.py#L1) |
| Portfolio decision | [tradingagents/agents/managers/portfolio_manager.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/managers/portfolio_manager.py#L1) |
| Rating vocabulary | [tradingagents/agents/rating.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/agents/rating.py#L1) |
| LLM providers | [tradingagents/llm_clients/factory.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/llm_clients/factory.py#L1) |
| Decision memory | [tradingagents/memory/log.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/memory/log.py#L1) |
| Reports | [tradingagents/reporting.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/reporting.py#L1) |
| Run checkpoints | [tradingagents/graph/checkpointer.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/graph/checkpointer.py#L1) |
| Data routing | [tradingagents/dataflows/router.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/dataflows/router.py#L1) |
| Yahoo market data | [tradingagents/dataflows/vendors/yahoo/market.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/dataflows/vendors/yahoo/market.py#L1) |
| Other data vendors | [tradingagents/dataflows/vendors/sec_edgar.py:1](https://github.com/TauricResearch/TradingAgents/blob/e8f5503e9b86d5c2710b0c76b1f686703968c9df/tradingagents/dataflows/vendors/sec_edgar.py#L1) |

The diagram does not represent a broker execution engine. Native backtests evaluate decisions; they do not maintain a cash ledger.
