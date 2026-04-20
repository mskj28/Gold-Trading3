import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model

# ===== LOAD MODEL =====
model = load_model("backend_model/xauusd_polygon_lstm_cv_final.keras")
feature_scaler = joblib.load("backend_model/polygon_feature_scaler.pkl")
price_scaler = joblib.load("backend_model/polygon_price_scaler.pkl")

# ===== LOAD DATA =====
df = pd.read_csv("data.csv")

# ต้องมี columns:
# close, sma_20, rsi, macd, volume

# ===== PREPARE INPUT =====
def prepare_input(window):
    features = window[["close", "sma_20", "rsi", "macd", "volume"]].values
    scaled = feature_scaler.transform(features)
    return np.reshape(scaled, (1, 60, scaled.shape[1]))

# ===== PREDICT =====
def predict_price(window):
    X = prepare_input(window)
    y_pred_scaled = model.predict(X, verbose=0)
    y_pred = price_scaler.inverse_transform(y_pred_scaled)
    return float(y_pred[0][0])

# ===== SIGNAL =====
def generate_signal(current, predicted):
    diff = (predicted - current) / current
    if diff > 0.002:
        return "BUY"
    elif diff < -0.002:
        return "SELL"
    else:
        return "HOLD"

# ===== BACKTEST =====
balance = 10000
position = 0
entry_price = 0

equity_curve = []
returns = []
wins = 0
trades = 0

for i in range(60, len(df)):
    window = df.iloc[i-60:i]
    current_price = df.iloc[i]["close"]

    predicted_price = predict_price(window)
    signal = generate_signal(current_price, predicted_price)

    # BUY
    if signal == "BUY" and position == 0:
        position = 1
        entry_price = current_price
        trades += 1

    # SELL
    elif signal == "SELL" and position == 1:
        profit = current_price - entry_price
        balance += profit

        returns.append(profit / entry_price)

        if profit > 0:
            wins += 1

        position = 0

    equity_curve.append(balance)

# ===== METRICS =====
win_rate = wins / trades if trades > 0 else 0

returns = np.array(returns)
sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 1 else 0

# Max Drawdown
equity_array = np.array(equity_curve)
peak = np.maximum.accumulate(equity_array)
drawdown = (equity_array - peak) / peak
max_drawdown = drawdown.min()

# ===== RESULT =====
print("Final Balance:", balance)
print("Win Rate:", round(win_rate, 2))
print("Sharpe Ratio:", round(sharpe_ratio, 2))
print("Max Drawdown:", round(max_drawdown, 2))

# ===== PLOT =====
plt.figure()
plt.plot(equity_curve)
plt.title("Equity Curve")
plt.xlabel("Time")
plt.ylabel("Balance")
plt.show()