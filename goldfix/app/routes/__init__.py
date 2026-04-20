from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os
import requests

from app.utils.logger import push_university_log

router = APIRouter()

PORTFOLIO_FILE = "portfolio.json"
TRADE_MIN_THB = 1000.00
BAHT_TO_GRAM = 15.244
STARTING_THB = 1500.00


class ExecuteRequest(BaseModel):
    ai_action: str
    ai_reason: str
    ai_amount_thb: str
    user_action: str


def load_portfolio() -> dict:
    default_state = {
        "THB_Balance": STARTING_THB,
        "Gold_Gram": 0.0,
        "Current_Date": str(datetime.now().date()),
        "Current_Period": "NONE",
        "Trades_Count": 0,
    }
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, default in default_state.items():
                data.setdefault(key, default)
            return data
        except Exception:
            pass
    return default_state


def save_portfolio(portfolio: dict) -> None:
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=4)


def get_live_hsh_data() -> dict | None:
    try:
        url = "https://apicheckpricev3.huasengheng.com/api/Values/GetPriceSeacon"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return {
            "HSH_Buy": float(data.get("Bid965", 0)),
            "HSH_Sell": float(data.get("Ask965", 0)),
            "Assoc_Buy": float(data.get("BidAssociation", 0)),
            "Assoc_Sell": float(data.get("AskAssociation", 0)),
        }
    except Exception:
        return None


def normalize_action(action: str) -> str:
    return (action or "").strip().upper()


@router.get("/ai/status")
async def ai_status():
    portfolio = load_portfolio()
    market_data = get_live_hsh_data()
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data unavailable")

    nav = portfolio["THB_Balance"] + (portfolio["Gold_Gram"] * (market_data["HSH_Buy"] / BAHT_TO_GRAM))
    return {
        "portfolio": portfolio,
        "market": market_data,
        "net_asset_value": nav,
    }


@router.post("/ai/analyze")
async def ai_analyze(request: Request):
    # The frontend currently sends an empty body, so we ignore payload contents.
    return {
        "ai_action": "BUY",
        "ai_amount_thb": "1000",
        "ai_reason": "Internal AI engine mock - use this response for frontend flow.",
        "confidence": 0.72,
        "raw_reports": [
            {"title": "Economics stable", "summary": "Market sentiment is neutral.", "sentiment": "neutral"},
        ],
    }


@router.post("/ai/execute")
async def ai_execute(req: ExecuteRequest):
    portfolio = load_portfolio()
    market_data = get_live_hsh_data()
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data unavailable")

    ai_action = normalize_action(req.ai_action)
    user_action = normalize_action(req.user_action)
    final_action = "HOLD"
    final_reason = req.ai_reason or "No reason provided."
    exec_price = "MARKET"
    exec_amount = "0"

    if ai_action == "HOLD" and user_action in {"BUY", "SELL"}:
        final_action = "HOLD"
        final_reason = f"[RULE 5 ENFORCED] AI signaled HOLD. User attempted {user_action}."
    elif user_action in {"HOLD", "TIMEOUT"}:
        final_action = "HOLD"
        final_reason = f"[{user_action}] User chose to hold against AI signal: {req.ai_reason}"
    elif user_action in {"BUY", "SELL"}:
        final_action = user_action
        if user_action != ai_action:
            final_reason = f"[USER OVERRIDE] {req.ai_reason}"

    if final_action == "BUY":
        if portfolio["THB_Balance"] >= TRADE_MIN_THB:
            if req.ai_amount_thb and req.ai_amount_thb.strip().upper() == "ALL":
                amount_thb = portfolio["THB_Balance"]
            else:
                try:
                    amount_thb = float(req.ai_amount_thb)
                except Exception:
                    amount_thb = TRADE_MIN_THB
            amount_thb = max(TRADE_MIN_THB, min(amount_thb, portfolio["THB_Balance"]))
            gram_bought = round(amount_thb / (market_data["HSH_Sell"] / BAHT_TO_GRAM), 4)
            portfolio["Gold_Gram"] += gram_bought
            portfolio["THB_Balance"] -= amount_thb
            portfolio["Trades_Count"] += 1
            exec_amount = f"{gram_bought}g ({amount_thb} THB)"
            exec_price = market_data["HSH_Sell"]
        else:
            final_action = "HOLD"
            final_reason = "Insufficient THB for BUY."

    elif final_action == "SELL":
        if portfolio["Gold_Gram"] > 0:
            gram_sold = portfolio["Gold_Gram"]
            cash_returned = round(gram_sold * (market_data["HSH_Buy"] / BAHT_TO_GRAM), 2)
            portfolio["THB_Balance"] += cash_returned
            portfolio["Gold_Gram"] = 0.0
            portfolio["Trades_Count"] += 1
            exec_amount = f"Sold {gram_sold:.4f}g ({cash_returned} THB)"
            exec_price = market_data["HSH_Buy"]
        else:
            final_action = "HOLD"
            final_reason = "No Gold to SELL."

    save_portfolio(portfolio)
    net_asset_value = portfolio["THB_Balance"] + (portfolio["Gold_Gram"] * (market_data["HSH_Buy"] / BAHT_TO_GRAM))

    try:
        push_university_log(action=final_action, price=exec_price, reason=final_reason)
    except Exception as exc:
        print(f"[ai_execute] log send failed: {exc}")

    return {
        "status": "success",
        "executed_action": final_action,
        "reason": final_reason,
        "executed_amount": exec_amount,
        "net_asset_value": net_asset_value,
    }


@router.get("/ai/logs")
async def ai_logs():
    return {"logs": []}
