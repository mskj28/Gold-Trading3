import yfinance as yf
import pandas as pd

# ดึงข้อมูลย้อนหลัง
df = yf.download("GC=F", period="1y", interval="1h")

# ===== สร้าง features =====
df["sma_20"] = df["Close"].rolling(20).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss
df["rsi"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["macd"] = ema12 - ema26

df["volume"] = df["Volume"]

# ===== clean =====
df = df.dropna()

# ===== rename =====
df = df.rename(columns={"Close": "close"})

# ===== save =====
df[["close", "sma_20", "rsi", "macd", "volume"]].to_csv("data.csv", index=False)

print("Saved data.csv")