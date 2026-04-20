from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any

import joblib
import numpy as np
from tensorflow.keras.layers import LSTM
from tensorflow.keras.models import load_model


# New implementation: Use the new AI agent's /api/analyze endpoint for predictions
import requests
from app.core.config import settings

def predict_price(feature_window, current_price: float) -> dict[str, Any]:
    """
    Calls the new AI agent's /api/analyze endpoint for prediction.
    """
    try:
        # You may need to adjust the URL if your agent runs on a different host/port
        agent_url = "http://localhost:8001/api/analyze"
        # Send any required data; here we just send a minimal payload
        # You can expand this to send feature_window/current_price if your agent expects it
        response = requests.post(agent_url, json={
            "feature_window": feature_window.to_dict() if hasattr(feature_window, 'to_dict') else str(feature_window),
            "current_price": current_price
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Map the agent's response to the expected format
        return {
            "predicted_price": data.get("predicted_price", current_price),
            "confidence": data.get("confidence", 0.5),
            "source": "ai_agent_webapp"
        }
    except Exception as exc:
        # Fallback: return current price with low confidence
        return {
            "predicted_price": current_price,
            "confidence": 0.1,
            "source": f"ai_agent_webapp_error: {exc}"
        }
