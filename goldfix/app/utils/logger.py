import os
import logging
import requests
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

LOG_API_URL = os.getenv("LOG_API_URL")
LOG_API_KEY = os.getenv("LOG_API_KEY")


def get_logger(name: str):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)


def _validate_log_payload(action: str, price, reason: str) -> tuple[str, object, str]:
    normalized_action = (action or "").strip().upper()
    if normalized_action not in {"BUY", "SELL", "HOLD"}:
        raise ValueError("action must be BUY, SELL, or HOLD")

    if price == "MARKET":
        validated_price = "MARKET"
    elif isinstance(price, bool):
        raise ValueError("price must be MARKET or a number")
    elif isinstance(price, (int, float)):
        validated_price = price
    else:
        try:
            validated_price = float(price)
        except Exception:
            raise ValueError("price must be MARKET or a number")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must not be empty")

    return normalized_action, validated_price, reason.strip()


def push_university_log(action: str, price, reason: str):
    action, price, reason = _validate_log_payload(action, price, reason)

    if not LOG_API_URL or not LOG_API_KEY:
        raise RuntimeError("Missing LOG_API_URL or LOG_API_KEY in environment")

    payload = {"action": action, "price": price, "reason": reason}
    headers = {
        "Authorization": f"Bearer {LOG_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(LOG_API_URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def send_log(action: str, price, reason: str):
    try:
        return push_university_log(action, price, reason)
    except Exception as exc:
        print(f"[logger] send_log skipped: {exc}")
        return None
