import os
import json
import requests
import feedparser
import pandas as pd
import numpy as np
import yfinance as yf
from groq import Groq
from datetime import datetime, time as dt_time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =====================================================================
# 1. CONFIGURATION
# =====================================================================
GROQ_API_KEY = "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"
PORTFOLIO_FILE = "portfolio.json"
LOG_FILE_NAME = "live_gold_log.json"
LANGUAGE = "EN"
BAHT_TO_GRAM = 15.244
TRADE_MIN_THB = 1000.00
STARTING_THB = 1500.00

TRADE_QUOTAS = {
    "WD_Morning": 2, "WD_Afternoon": 2, "WD_Evening": 2, "WE_Active": 2
}

client = Groq(api_key=GROQ_API_KEY)

# =====================================================================
# 2. FASTAPI SETUP
# =====================================================================
app = FastAPI(title="AI Gold Trading API")

# Enable CORS so React can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models for React Requests
class ExecutionRequest(BaseModel):
    action: str  # "BUY", "SELL", "HOLD"
    ai_reason: str
    is_user_override: bool


# =====================================================================
# 3. HELPER FUNCTIONS (Same as before)
# =====================================================================
def get_trading_period(now):
    weekday = now.weekday()
    current_time = now.time()
    current_date = now.date()
    if weekday < 5:
        if dt_time(6, 0) <= current_time <= dt_time(11, 59, 59):
            return "WD_Morning", "Weekday Morning", True, datetime.combine(current_date, dt_time(11, 59, 59))
        elif dt_time(12, 0) <= current_time <= dt_time(17, 59, 59):
            return "WD_Afternoon", "Weekday Afternoon", True, datetime.combine(current_date, dt_time(17, 59, 59))
        elif dt_time(18, 0) <= current_time <= dt_time(23, 59, 59):
            return "WD_Evening", "Weekday Evening", True, datetime.combine(current_date, dt_time(23, 59, 59))
    else:
        if dt_time(9, 30) <= current_time <= dt_time(17, 29, 59):
            return "WE_Active", "Weekend Active", True, datetime.combine(current_date, dt_time(17, 29, 59))
    return "CLOSED", "Out of Trading Hours", False, None


def load_portfolio():
    default_state = {"THB_Balance": STARTING_THB, "Gold_Gram": 0.0, "Current_Date": str(datetime.now().date()),
                     "Current_Period": "NONE", "Trades_Count": 0}
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            try:
                data = json.load(f)
                for k, v in default_state.items():
                    if k not in data: data[k] = v
                return data
            except:
                pass
    return default_state


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)


def get_live_hsh_data():
    try:
        url = "https://apicheckpricev3.huasengheng.com/api/Values/GetPriceSeacon"
        data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        return {'HSH_Buy': float(data.get('Bid965', 0)), 'HSH_Sell': float(data.get('Ask965', 0)),
                'Assoc_Buy': float(data.get('BidAssociation', 0)), 'Assoc_Sell': float(data.get('AskAssociation', 0))}
    except:
        return None


# (Note: For brevity, assume get_global_markets, get_news, and ask_groq are here, exactly as they were in your script)

# =====================================================================
# 4. API ENDPOINTS
# =====================================================================

@app.get("/api/status")
def get_status():
    """React calls this to show the dashboard (Cash, Gold, Prices)."""
    now = datetime.now()
    portfolio = load_portfolio()
    market_data = get_live_hsh_data()
    period_key, period_name, is_active, end_time = get_trading_period(now)

    # Portfolio reset logic
    if portfolio.get('Current_Date') != str(now.date()) or portfolio.get('Current_Period') != period_key:
        portfolio['Current_Date'] = str(now.date())
        portfolio['Current_Period'] = period_key
        portfolio['Trades_Count'] = 0
        save_portfolio(portfolio)

    if not market_data:
        raise HTTPException(status_code=503, detail="Market Data Unavailable")

    price_per_gram_buy = market_data['HSH_Sell'] / BAHT_TO_GRAM
    price_per_gram_sell = market_data['HSH_Buy'] / BAHT_TO_GRAM
    nav = portfolio['THB_Balance'] + (portfolio['Gold_Gram'] * price_per_gram_sell)

    return {
        "portfolio": portfolio,
        "market": market_data,
        "prices_per_gram": {"buy": price_per_gram_buy, "sell": price_per_gram_sell},
        "net_asset_value": nav,
        "period": {
            "is_active": is_active,
            "name": period_name,
            "trades_done": portfolio['Trades_Count'],
            "target_trades": TRADE_QUOTAS.get(period_key, 0)
        }
    }


@app.post("/api/analyze")
def generate_ai_signal():
    """React calls this to trigger Groq AI and get a recommendation."""
    # 1. Gather all data
    # ... (Run your get_global_markets, get_news, get_live_hsh_data here) ...
    # 2. Build prompt with dynamic urgency
    # 3. Call ask_groq()

    # Mocking the AI response structure for the API example:
    return {
        "ai_action": "BUY",
        "ai_reason": "RSI shows oversold conditions.",
        "raw_reports": {
            "eco": "Economy stable.",
            "quant": "Momentum shifting upwards."
        }
    }


@app.post("/api/execute")
def execute_trade(req: ExecutionRequest):
    """React calls this when the User clicks Buy/Sell/Hold OR when the timer hits 0."""
    portfolio = load_portfolio()
    market_data = get_live_hsh_data()
    price_per_gram_buy = market_data['HSH_Sell'] / BAHT_TO_GRAM
    price_per_gram_sell = market_data['HSH_Buy'] / BAHT_TO_GRAM

    act = "HOLD"
    exec_amount = "0"
    reason = req.ai_reason if not req.is_user_override else f"[USER OVERRIDE] {req.action}"

    if req.action == "BUY" and portfolio['THB_Balance'] >= TRADE_MIN_THB:
        act = "BUY"
        gram_bought = round(portfolio['THB_Balance'] / price_per_gram_buy, 4)
        exec_amount = f"{gram_bought} Grams"
        portfolio['Gold_Gram'] += gram_bought
        portfolio['THB_Balance'] = 0.0
        portfolio['Trades_Count'] += 1

    elif req.action == "SELL" and portfolio['Gold_Gram'] > 0:
        act = "SELL"
        cash_returned = round(portfolio['Gold_Gram'] * price_per_gram_sell, 2)
        exec_amount = f"Sold {portfolio['Gold_Gram']:.4f} Grams"
        portfolio['THB_Balance'] += cash_returned
        portfolio['Gold_Gram'] = 0.0
        portfolio['Trades_Count'] += 1

    elif req.action != "HOLD":
        return {"status": "error", "message": "Insufficient funds or gold."}

    save_portfolio(portfolio)

    # Build Log Entry and save to JSON file here...

    return {"status": "success", "executed_action": act, "amount": exec_amount}


@app.get("/api/logs")
def get_logs():
    """React calls this to populate the trading history table."""
    if os.path.exists(LOG_FILE_NAME):
        with open(LOG_FILE_NAME, "r") as f:
            return json.load(f)
    return []