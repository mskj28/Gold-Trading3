from fastapi import FastAPI, APIRouter, Request

from app.core.config import settings
from app.routes.analysis import router as analysis_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.market import router as market_router
from app.routes.predict import router as predict_router
from app.routes.risk import router as risk_router
from app.routes.usdthb import usdthb_router

# 🔥 AI proxy
from app.routes import router as ai_proxy_router

from datetime import datetime, timezone, timedelta
import json
from datetime import datetime

import sqlite3

# 🔥 สร้าง/เชื่อม DB
conn = sqlite3.connect("logs.db", check_same_thread=False)
cursor = conn.cursor()

# 🔥 สร้าง table ถ้ายังไม่มี
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    price REAL,
    reason TEXT,
    timestamp TEXT
)
""")
conn.commit()

LOG_FILE = "logs.json"
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# ================= ROUTERS =================
app.include_router(health_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(predict_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(usdthb_router, prefix="/api")
app.include_router(ai_proxy_router, prefix="/api")

# ================= LOG SYSTEM =================
log_router = APIRouter()

@log_router.post("/logs")
async def receive_log(request: Request):
    data = await request.json()

    # ✅ เพิ่มเวลา
    timestamp = datetime.utcnow().isoformat()

    print("RECEIVED LOG:", data)

    # 🔥 insert ลง database
    cursor.execute(
        "INSERT INTO logs (action, price, reason, timestamp) VALUES (?, ?, ?, ?)",
        (data["action"], data["price"], data["reason"], timestamp)
    )
    conn.commit()

    return {"status": "ok"}


@log_router.get("/logs")
def get_logs():
    cursor.execute("SELECT * FROM logs ORDER BY id DESC")
    rows = cursor.fetchall()

    # แปลงเป็น dict
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "action": row[1],
            "price": row[2],
            "reason": row[3],
            "timestamp": row[4],
        })

    return result


# 🔥 include log router
app.include_router(log_router, prefix="/api")


# ================= ROOT =================
@app.get("/")
def root():
    return {
        "message": "Gold Trading AI API is running",
        "docs": "/docs",
        "version": settings.APP_VERSION,
        "mode": "real_model_with_risk_overlay",
    }