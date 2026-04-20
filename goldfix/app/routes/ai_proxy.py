import os
import json
import requests
import feedparser
import yfinance as yf
import numpy as np
from datetime import datetime, time as dt_time, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import Groq

# =====================================================================
# 1. CONFIGURATION & STATE
# =====================================================================
router = APIRouter(prefix="/ai", tags=["AI Proxy"])

GROQ_API_KEYS = [
    "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",
    "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",
    "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"
]

ENABLE_UNIVERSITY_API = True
TEAM_API_KEY = "6e2755d365cb0e408024ddaca46aadf28756bd9c2a7481de70c82adeff2b436c"
LOG_BASE_URL = "https://goldtrade-logs-api.poonnatuch.workers.dev"

STARTING_THB = 1500.00
TRADE_MIN_THB = 1000.00
PORTFOLIO_FILE = "portfolio.json"
BAHT_TO_GRAM = 15.244
LANGUAGE = "EN"


# =====================================================================
# 2. MODELS
# =====================================================================
class ExecuteRequest(BaseModel):
    ai_action: str
    ai_reason: str
    ai_amount_thb: str
    user_action: str


class PortfolioUpdate(BaseModel):
    THB_Balance: float
    Gold_Gram: float


# =====================================================================
# 3. HELPER FUNCTIONS
# =====================================================================
def load_portfolio():
    default_state = {"THB_Balance": STARTING_THB, "Gold_Gram": 0.0, "Trades_Count": 0}
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
        return {
            'HSH_Buy': float(data.get('Bid965', 0)),
            'HSH_Sell': float(data.get('Ask965', 0)),
            'Assoc_Buy': float(data.get('BidAssociation', 0)),
            'Assoc_Sell': float(data.get('AskAssociation', 0))
        }
    except:
        # Fallback หาก API ของฮั่วเซ่งเฮงมีปัญหา
        return {'HSH_Buy': 41000, 'HSH_Sell': 41030, 'Assoc_Buy': 41000, 'Assoc_Sell': 41000}


def get_global_markets():
    try:
        # แก้ไขบัค Yahoo Finance ด้วย 3mo และ MGC=F
        gold_hist = None
        for ticker in ["GC=F", "MGC=F"]:
            try:
                temp_hist = yf.Ticker(ticker).history(period="3mo")['Close']
                if len(temp_hist) >= 50:
                    gold_hist = temp_hist
                    break
            except:
                continue

        if gold_hist is None:
            # Fallback to synthetic data if Yahoo Finance fails
            import numpy as np
            import pandas as pd
            dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='D')
            # Simulate gold price around 41000 THB with some volatility
            base_price = 41000
            noise = np.random.normal(0, 500, len(dates))
            trend = np.linspace(0, 1000, len(dates))  # Slight upward trend
            gold_hist = pd.Series(base_price + trend + noise, index=dates)

        ema_fast = gold_hist.ewm(span=14, adjust=False).mean().iloc[-1]
        ema_slow = gold_hist.ewm(span=50, adjust=False).mean().iloc[-1]

        delta = gold_hist.diff()
        up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        down = -1 * delta.clip(upper=0).ewm(alpha=1 / 14, adjust=False).mean()
        rsi = 100 - (100 / (1 + (up / down))).iloc[-1]

        thb_hist = yf.Ticker("THB=X").history(period="14d")['Close']
        current_thb = thb_hist.iloc[-1] if not thb_hist.empty else 36.5  # Fallback THB rate

        return {
            "xau_price": gold_hist.iloc[-1], "rsi": rsi,
            "ema_signal": "BULLISH" if ema_fast > ema_slow else "BEARISH",
            "current_thb": current_thb, "thb_trend": "VOLATILE"
        }
    except:
        # Ultimate fallback with synthetic data
        return {
            "xau_price": 41000, "rsi": 55,
            "ema_signal": "BULLISH",
            "current_thb": 36.5, "thb_trend": "VOLATILE"
        }


def ask_groq(prompt):
    models = ["llama-3.1-8b-instant"]
    for api_key in GROQ_API_KEYS:
        try:
            client = Groq(api_key=api_key)
            res = client.chat.completions.create(
                messages=[
                    {"role": "system",
                     "content": "You are a quantitative commodities strategist. Respond strictly in English."},
                    {"role": "user", "content": prompt}
                ],
                model=models[0], temperature=0.1, max_tokens=250
            )
            return res.choices[0].message.content
        except:
            continue
    return "ACTION: HOLD\nAMOUNT_THB: 0\nREASONING: Groq API Error."


def push_log_to_server(action, price, reason, amount, current_nav, ai_action, user_action):
    if not ENABLE_UNIVERSITY_API: return
    payload = {
        "action": action,
        "price": "MARKET" if price == "MARKET" else float(price),
        "reason": reason,
        "executed_amount": amount,
        "net_asset_value": current_nav,
        "signal_source": "AI_Agent_WebApp",
        "ai_intended_action": ai_action,
        "user_override_action": user_action
    }
    try:
        requests.post(f"{LOG_BASE_URL}/logs", headers={"Authorization": f"Bearer {TEAM_API_KEY}"}, json=payload,
                      timeout=5)
    except:
        pass


# =====================================================================
# 4. ENDPOINTS
# =====================================================================
@router.get("/status")
def get_status():
    """App.jsx เรียกทุกๆ วินาทีเพื่อโหลด Portfolio และ Live Market"""
    portfolio = load_portfolio()
    market = get_live_hsh_data()
    nav = portfolio['THB_Balance'] + (portfolio['Gold_Gram'] * (market['HSH_Buy'] / BAHT_TO_GRAM))

    return {"portfolio": portfolio, "market": market, "net_asset_value": nav}


@router.post("/portfolio")
def update_portfolio(req: PortfolioUpdate):
    """App.jsx เรียกเพื่อบันทึกค่าพอร์ตการลงทุนใหม่ผ่านหน้าเว็บ"""
    portfolio = load_portfolio()

    portfolio['THB_Balance'] = req.THB_Balance
    portfolio['Gold_Gram'] = req.Gold_Gram

    save_portfolio(portfolio)

    return {
        "status": "success",
        "message": "Portfolio updated successfully",
        "portfolio": portfolio
    }


@router.post("/analyze")
def trigger_analysis():
    """App.jsx เรียกเมื่อกดปุ่ม Trigger AI หรือ Timer นับถอยหลังถึง 0"""
    market = get_live_hsh_data()
    global_math = get_global_markets()
    portfolio = load_portfolio()

    if not global_math:
        return {"error": "Market Data Offline", "ai_action": "HOLD"}

    p_buy = market['HSH_Sell'] / BAHT_TO_GRAM
    p_sell = market['HSH_Buy'] / BAHT_TO_GRAM

    # ดึงข่าวจำลองเพื่อส่งให้ Frontend (สามารถเชื่อม API ข่าวจริงได้ที่นี่)
    news_items = [{"title": "Gold Markets Active", "summary": "Investors await data.", "sentiment": "neutral"}]

    # สร้าง AI Prompt (Aggressive Strategy)
    prompt = f"""
    Portfolio Manager. Cash: {portfolio['THB_Balance']} THB. Gold: {portfolio['Gold_Gram']}g.
    Buy Price: {p_buy} | Sell Price: {p_sell}
    XAUUSD: ${global_math['xau_price']} | RSI: {global_math['rsi']} | EMA: {global_math['ema_signal']}
    USD/THB: {global_math['current_thb']}

    Constraint: You CANNOT BUY if Cash < {TRADE_MIN_THB}. You CANNOT SELL if Gold Held is 0.
    Strategy: You are a Scalper. If RSI < 45, BUY IMMEDIATELY using minimum {TRADE_MIN_THB} THB. If RSI > 55 or there is a small profit, SELL IMMEDIATELY.
    FORMAT:
    ACTION: [BUY / SELL / HOLD]
    AMOUNT_THB: [Enter number or ALL]
    REASONING: [1 sentence logic.]
    """

    decision = ask_groq(prompt)

    ai_act, ai_reason, ai_amt = "HOLD", "Default", "ALL"
    for line in decision.split('\n'):
        line_u = line.upper()
        if "ACTION:" in line_u:
            if "BUY" in line_u:
                ai_act = "BUY"
            elif "SELL" in line_u:
                ai_act = "SELL"
        elif "AMOUNT_THB:" in line_u:
            parts = line.split(":", 1)
            if len(parts) > 1: ai_amt = parts[1].strip().replace(',', '')
        elif "REASONING:" in line_u:
            parts = line.split(":", 1)
            if len(parts) > 1: ai_reason = parts[1].strip()

    return {
        "ai_action": ai_act,
        "ai_amount_thb": ai_amt,
        "ai_reason": ai_reason,  # ตัวแปรนี้จะถูกส่งไปโชว์ใน Frontend แทน Confidence
        "raw_reports": news_items
    }


@router.post("/execute")
def execute_trade(req: ExecuteRequest):
    """App.jsx เรียกเมื่อผู้ใช้กด Force BUY/SELL/HOLD หรือ Timeout"""
    portfolio = load_portfolio()
    market = get_live_hsh_data()

    p_buy = market['HSH_Sell'] / BAHT_TO_GRAM
    p_sell = market['HSH_Buy'] / BAHT_TO_GRAM

    final_act = req.ai_action if req.user_action == "TIMEOUT" else req.user_action
    if final_act not in ["BUY", "SELL"]: final_act = "HOLD"

    act, exec_price, exec_amt_str = "HOLD", "MARKET", "0"

    if final_act == "BUY" and portfolio['THB_Balance'] >= TRADE_MIN_THB:
        target_thb = portfolio['THB_Balance']
        if req.ai_amount_thb != "ALL":
            try:
                target_thb = float(req.ai_amount_thb)
            except:
                pass

        target_thb = max(TRADE_MIN_THB, min(target_thb, portfolio['THB_Balance']))
        gram_bought = round(target_thb / p_buy, 4)

        portfolio['Gold_Gram'] += gram_bought
        portfolio['THB_Balance'] -= target_thb
        act, exec_price = "BUY", market['HSH_Sell']
        exec_amt_str = f"{gram_bought}g ({target_thb} THB)"

    elif final_act == "SELL" and portfolio['Gold_Gram'] > 0:
        gram_sold = portfolio['Gold_Gram']
        cash_returned = round(gram_sold * p_sell, 2)
        portfolio['THB_Balance'] += cash_returned
        portfolio['Gold_Gram'] -= gram_sold
        act, exec_price = "SELL", market['HSH_Buy']
        exec_amt_str = f"Sold {gram_sold}g ({cash_returned} THB)"

    save_portfolio(portfolio)
    nav = portfolio['THB_Balance'] + (portfolio['Gold_Gram'] * p_sell)

    # ส่ง Log เข้า Server มหาวิทยาลัย (ถ้า ENABLE_UNIVERSITY_API = True)
    push_log_to_server(act, exec_price, req.ai_reason, exec_amt_str, nav, req.ai_action, req.user_action)

    return {
        "status": "success",
        "executed_action": act,
        "reason": f"System processed {act}. Original intent: {req.ai_action}",
        "executed_amount": exec_amt_str,
        "net_asset_value": nav
    }