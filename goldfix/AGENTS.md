# AI Agent Instructions
- Architecture: FastAPI service for gold market analysis and model inference.
- Math first: Compute RSI, EMA, MACD, returns, drawdown, EV, and Kelly deterministically in Python.
- LLM safety principle: Never ask the LLM to calculate indicators.
- Trading safety: Never place live orders. Return recommendations only.
- Model note: The shipped LSTM expects a 60-step sequence with 2 features: `Close`, `News_Sentiment`.
- Validation: Enforce max position and drawdown constraints in the execution/risk layer.
