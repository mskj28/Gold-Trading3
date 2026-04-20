from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.core.config import settings


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    excess = returns - risk_free_rate
    std = excess.std(ddof=0)
    if std == 0 or math.isnan(std):
        return 0.0
    return float(excess.mean() / std)


def sortino_ratio(returns: pd.Series, target_return: float = 0.0) -> float:
    downside = (returns - target_return).clip(upper=0)
    downside_dev = (downside.pow(2).mean()) ** 0.5
    if downside_dev == 0 or math.isnan(downside_dev):
        return 0.0
    return float((returns.mean() - target_return) / downside_dev)


def max_drawdown(equity_curve: pd.Series) -> float:
    running_peak = equity_curve.cummax()
    drawdown = (running_peak - equity_curve) / running_peak.replace(0, pd.NA)
    return float(drawdown.max(skipna=True) or 0.0)


def expected_value(win_rate: float, avg_win: float, avg_loss: float) -> float:
    loss_rate = 1.0 - win_rate
    return float((win_rate * avg_win) - (loss_rate * avg_loss))


def kelly_fraction(win_rate: float, reward_risk_ratio: float) -> float:
    if reward_risk_ratio <= 0:
        return 0.0
    raw = win_rate - ((1.0 - win_rate) / reward_risk_ratio)
    return float(max(0.0, raw))


def build_backtest_preview(df: pd.DataFrame) -> dict[str, float]:
    close = pd.to_numeric(df["Close"], errors="coerce")
    returns = close.pct_change().dropna()
    if returns.empty:
        return {"sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0}
    return {
        "sharpe": round(sharpe_ratio(returns), 6),
        "sortino": round(sortino_ratio(returns), 6),
        "max_drawdown": round(max_drawdown(close), 6),
    }


def build_trade_risk_overlay(
    *,
    capital: float,
    current_price: float,
    predicted_price: float,
    rolling_volatility: float,
    current_drawdown: float,
) -> dict[str, Any]:
    expected_change = predicted_price - current_price
    expected_change_pct = (expected_change / current_price) if current_price else 0.0

    inferred_win_rate = min(0.75, max(0.35, 0.5 + (expected_change_pct * 4)))
    reward_risk_ratio = max(0.5, min(3.0, abs(expected_change_pct) / max(rolling_volatility, 0.005)))
    ev = expected_value(inferred_win_rate, abs(expected_change_pct), abs(expected_change_pct) / max(reward_risk_ratio, 1e-9))
    full_kelly = kelly_fraction(inferred_win_rate, reward_risk_ratio)
    half_kelly = full_kelly * settings.KELLY_FRACTION

    max_position_value = capital * settings.MAX_POSITION_PCT
    kelly_position_value = capital * half_kelly
    suggested_position_value = max(0.0, min(max_position_value, kelly_position_value))
    suggested_units = suggested_position_value / current_price if current_price else 0.0

    trading_blocked = abs(current_drawdown) >= settings.MAX_DRAWDOWN_LIMIT

    return {
        "expected_value": round(ev, 6),
        "inferred_win_rate": round(inferred_win_rate, 6),
        "reward_risk_ratio": round(reward_risk_ratio, 6),
        "full_kelly_fraction": round(full_kelly, 6),
        "half_kelly_fraction": round(half_kelly, 6),
        "max_position_value": round(max_position_value, 2),
        "suggested_position_value": round(suggested_position_value, 2),
        "suggested_units": round(suggested_units, 6),
        "drawdown_limit": settings.MAX_DRAWDOWN_LIMIT,
        "trading_blocked": trading_blocked,
    }
