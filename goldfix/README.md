# Gold Trading AI API v2

FastAPI backend สำหรับโปรเจค AI เทรดทอง โดยพัฒนาต่อจากโครงสร้างเดิมและเพิ่มแนวคิดจากสไลด์ เช่น
- deterministic feature engineering (EMA, MACD, RSI)
- structured market state
- risk-aware recommendation (EV, Kelly, max position cap, drawdown guard)
- real model inference จากไฟล์ `.keras` และ `.pkl`

## Project structure

```text
gold_trading_api_improved/
├── .env
├── AGENTS.md
├── requirements.txt
└── app/
    ├── main.py
    ├── artifacts/
    │   ├── xauusd_polygon_lstm_cv_final.keras
    │   ├── polygon_feature_scaler.pkl
    │   └── polygon_price_scaler.pkl
    ├── core/
    ├── routes/
    ├── schemas/
    ├── services/
    └── utils/
```

## Setup

1. สร้าง virtualenv และติดตั้ง package
```bash
pip install -r requirements.txt
```

2. วาง model artifacts ลงใน `app/artifacts/`
- `xauusd_polygon_lstm_cv_final.keras`
- `polygon_feature_scaler.pkl`
- `polygon_price_scaler.pkl`

3. Run API
```bash
uvicorn app.main:app --reload
```

Swagger docs: `http://127.0.0.1:8000/docs`

## Main endpoints
- `GET /api/health`
- `GET /api/market/gold`
- `GET /api/predict/gold`
- `GET /api/analysis/gold`
- `GET /api/risk/backtest-preview`

## Example
```bash
curl "http://127.0.0.1:8000/api/analysis/gold?symbol=XAUUSD&period=6mo&interval=1d&capital=10000"
```

## Design notes
- Model inference ใช้ feature ตามที่ scaler ระบุ: `Close`, `News_Sentiment`
- RSI / MACD ใช้เพื่อวิเคราะห์และ risk overlay ไม่ได้ยัดเพิ่มเข้า model ตรง ๆ เพราะจะทำให้ shape ไม่ตรงกับ model เดิม
- ระบบนี้ยัง **ไม่ส่งคำสั่งเทรดจริง** แต่ให้ recommendation พร้อมขนาด position ที่แนะนำ
