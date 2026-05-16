import numpy as np
import pandas as pd
from datetime import datetime

def days_until_month_end(date):
    year = date.year
    month = date.month
    if month == 12:
        next_month_end = datetime(year+1, 1, 1) - pd.Timedelta(days=1)
    else:
        next_month_end = datetime(year, month+1, 1) - pd.Timedelta(days=1)
    return max(1, (next_month_end - date).days)

def compute_price_bridge_signal(current_price, target_price, days_to_target, volatility):
    T = days_to_target / 252.0
    mu = (np.log(target_price / current_price) / T) - 0.5 * volatility**2
    return mu

def compute_volatility_bridge_signal(current_vol, target_vol, days_to_target, vol_of_vol=0.5):
    return (target_vol - current_vol) / days_to_target

def get_month_end_target(price_series, current_date, use_market_target=False, market_series=None):
    if use_market_target and market_series is not None:
        # Use market index level as target
        target = market_series.asof(current_date - pd.Timedelta(days=1))
        if pd.isna(target):
            target = market_series.iloc[-1]
        return target
    else:
        # Own price target: last price at previous month‑end
        year = current_date.year
        month = current_date.month
        if month == 1:
            prev_month_end = datetime(year-1, 12, 31)
        else:
            prev_month_end = datetime(year, month-1, 1) + pd.offsets.MonthEnd(0)
        target = price_series.asof(prev_month_end)
        if pd.isna(target):
            target = price_series.iloc[0]
        return target

def compute_etf_signal(price_series, current_date, window=60, bridge_type="price",
                       use_market_target=False, market_series=None):
    if len(price_series) < window:
        return None
    recent = price_series.iloc[-window:]
    current_price = recent.iloc[-1]
    log_ret = np.log(recent / recent.shift(1)).dropna()
    volatility = log_ret.std() * np.sqrt(252)
    days_to_target = days_until_month_end(current_date)
    if bridge_type == "price":
        target_price = get_month_end_target(price_series, current_date,
                                            use_market_target=use_market_target,
                                            market_series=market_series)
        if target_price is None or target_price <= 0:
            return None
        drift = compute_price_bridge_signal(current_price, target_price, days_to_target, volatility)
        signal = drift
    else:  # volatility bridge
        vol_series = price_series.pct_change().rolling(window).std() * np.sqrt(252)
        current_vol = vol_series.iloc[-1]
        long_vol = price_series.pct_change().std() * np.sqrt(252)
        target_vol = long_vol
        signal = compute_volatility_bridge_signal(current_vol, target_vol, days_to_target)
        drift = None
        target_price = target_vol
        current_price = current_vol

    return {
        "signal": float(signal),
        "drift": float(drift) if drift is not None else None,
        "target": float(target_price),
        "current": float(current_price),
        "days_to_target": int(days_to_target),
        "volatility": float(volatility)
    }
