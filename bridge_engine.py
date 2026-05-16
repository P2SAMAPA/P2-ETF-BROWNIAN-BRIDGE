import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime

def days_until_month_end(date):
    """Number of trading days until the next month‑end (approximate using calendar days)."""
    # For simplicity, use calendar days; can be refined with trading calendar.
    year = date.year
    month = date.month
    if month == 12:
        next_month_end = datetime(year+1, 1, 1) - pd.Timedelta(days=1)
    else:
        next_month_end = datetime(year, month+1, 1) - pd.Timedelta(days=1)
    return max(1, (next_month_end - date).days)

def compute_price_bridge_signal(price_series, current_price, target_price, days_to_target, volatility):
    """
    Geometric Brownian bridge drift.
    For a process dS/S = μ dt + σ dW, conditioned on S(T) = target.
    The required drift μ = (log(target) - log(current_price)) / (T) - σ²/2.
    Return the drift (annualised) – positive = bullish.
    """
    if days_to_target <= 0:
        return 0.0
    T = days_to_target / 252.0   # annualised time
    mu = (np.log(target_price / current_price) / T) - 0.5 * volatility**2
    return mu

def compute_volatility_bridge_signal(vol_series, current_vol, target_vol, days_to_target, vol_of_vol=0.5):
    """
    Bridge on volatility: assume volatility follows a mean‑reverting process.
    Signal = (target_vol - current_vol) / days_to_target (simplified).
    Positive = volatility expected to rise.
    """
    if days_to_target <= 0:
        return 0.0
    signal = (target_vol - current_vol) / days_to_target
    return signal

def get_month_end_target(prices, ticker, current_date, use_market_target=False, market_ticker="SPY"):
    """Get the target price: last price at previous month‑end."""
    # Find the last trading day of the previous month
    if use_market_target:
        # use market index (e.g., SPY) as target – then target is relative
        # For each ETF, target = price of market index at last month‑end
        # Simpler: compute ratio ETF/market and target ratio = 1? Not needed.
        # We'll use the market level as the target.
        target = prices[market_ticker].asof(current_date - pd.Timedelta(days=1))
        return target
    else:
        # own price target: last price before current date (end of previous month)
        # Find last price in the previous month
        year = current_date.year
        month = current_date.month
        if month == 1:
            prev_month_end = datetime(year-1, 12, 31)
        else:
            prev_month_end = datetime(year, month-1, 1) + pd.offsets.MonthEnd(0)
        # Get price as of that day (or nearest)
        target = prices[ticker].asof(prev_month_end)
        if pd.isna(target):
            # fallback: first price in the series
            target = prices[ticker].iloc[0]
        return target

def compute_etf_signal(price_series, current_date, window=60, bridge_type="price",
                       use_market_target=False, market_ticker="SPY"):
    """
    Compute Brownian bridge signal for one ETF.
    Returns (signal, drift, target, current_price, days_to_target, volatility)
    """
    # Get last `window` days of prices
    if len(price_series) < window:
        return None
    recent = price_series.iloc[-window:]
    # Current price (last available)
    current_price = recent.iloc[-1]
    # Estimate volatility from log returns over the window
    log_ret = np.log(recent / recent.shift(1)).dropna()
    volatility = log_ret.std() * np.sqrt(252)   # annualised
    # Days to next month‑end
    days_to_target = days_until_month_end(current_date)
    if bridge_type == "price":
        target_price = get_month_end_target(pd.DataFrame(price_series).T, price_series.name,
                                            current_date, use_market_target, market_ticker)
        if target_price is None or target_price <= 0:
            return None
        drift = compute_price_bridge_signal(price_series, current_price, target_price,
                                            days_to_target, volatility)
        signal = drift   # positive drift = bullish
    else:  # volatility bridge
        # Target volatility: long‑term mean of volatility (e.g., last 252 days)
        long_vol = price_series.pct_change().std() * np.sqrt(252)
        vol_series = price_series.pct_change().rolling(window).std() * np.sqrt(252)
        current_vol = vol_series.iloc[-1]
        target_vol = long_vol
        signal = compute_volatility_bridge_signal(vol_series, current_vol, target_vol,
                                                  days_to_target, vol_of_vol=0.5)
    return {
        "signal": float(signal),
        "drift": float(drift) if bridge_type == "price" else None,
        "target": float(target_price) if bridge_type == "price" else float(target_vol),
        "current": float(current_price) if bridge_type == "price" else float(current_vol),
        "days_to_target": int(days_to_target),
        "volatility": float(volatility)
    }
