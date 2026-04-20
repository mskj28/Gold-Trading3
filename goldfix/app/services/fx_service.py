import yfinance as yf

def get_usdthb_rate() -> float:
    ticker = "USDTHB=X"
    df = yf.download(ticker, period="1d", interval="5m", progress=False, threads=False)

    if df is None or df.empty:
        raise ValueError("No USDTHB data")

    return float(df["Close"].iloc[-1])