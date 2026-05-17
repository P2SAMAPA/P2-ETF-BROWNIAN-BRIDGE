import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import config
import data_manager
from bridge_engine import compute_etf_signal

def main():
    if not config.HF_TOKEN:
        print("HF_TOKEN not set")
        return

    df = data_manager.load_master_data()
    all_results = {}
    today = datetime.now().strftime("%Y-%m-%d")

    for universe_name, tickers in config.UNIVERSES.items():
        print(f"\n=== Universe: {universe_name} (Brownian Bridge) ===")
        prices = data_manager.prepare_price_matrix(df, tickers)
        if prices.empty or len(prices) < max(config.WINDOWS) + config.ESTIMATION_WINDOW + 10:
            print("  Insufficient data")
            all_results[universe_name] = {"top_etfs": []}
            continue

        best_per_etf = {}
        window_results = {}

        for win in config.WINDOWS:
            if len(prices) < win + config.ESTIMATION_WINDOW + 10:
                print(f"  Skipping window {win}d (insufficient data)")
                continue
            print(f"  Processing window {win}d...")
            # Use last `win` days of price data (the estimation window is fixed inside compute_etf_signal)
            etf_signals = {}
            for etf in tickers:
                if etf not in prices.columns:
                    continue
                price_series = prices[etf].dropna()
                if len(price_series) < win + config.ESTIMATION_WINDOW:
                    continue
                # Use the last `win` days of data for the bridge, but the estimation window (e.g., 60d) is inside compute_etf_signal
                # We need to pass the most recent date and the price series slice.
                # We'll take the last `win` days as the price history for computing the bridge.
                prices_slice = price_series.iloc[-win:]
                # Current date is the last date of the slice
                current_date = prices_slice.index[-1]
                # Market series for target (if using market target)
                market_series = None
                if config.USE_MARKET_TARGET and config.TARGET_INDEX in prices.columns:
                    market_series = prices[config.TARGET_INDEX]
                result = compute_etf_signal(
                    prices_slice, current_date,
                    window=config.ESTIMATION_WINDOW,
                    bridge_type=config.BRIDGE_TYPE,
                    use_market_target=config.USE_MARKET_TARGET,
                    market_series=market_series
                )
                if result is None:
                    continue
                signal = result["signal"]
                etf_signals[etf] = signal
            window_results[win] = etf_signals
            for etf, sig in etf_signals.items():
                if etf not in best_per_etf or sig > best_per_etf[etf][0]:
                    best_per_etf[etf] = (sig, win)

        if not best_per_etf:
            print("  No valid predictions – falling back to historical mean return")
            returns = data_manager.prepare_returns_matrix(df, tickers)
            for etf in tickers:
                if etf in returns.columns:
                    mean_ret = returns[etf].iloc[-252:].mean()
                    if not np.isnan(mean_ret):
                        best_per_etf[etf] = (max(mean_ret, 1e-6), 0)
            if not best_per_etf:
                all_results[universe_name] = {"top_etfs": []}
                continue

        # Store full scores for all ETFs
        full_scores = {ticker: {"score": score, "best_window": win} for ticker, (score, win) in best_per_etf.items()}
        sorted_etfs = sorted(best_per_etf.items(), key=lambda x: x[1][0], reverse=True)
        top_etfs = [{"ticker": ticker, "signal": float(score), "best_window": win} for ticker, (score, win) in sorted_etfs[:config.TOP_N]]

        print(f"  Top 3 ETFs by bridge signal: {[e['ticker'] for e in top_etfs]}")
        all_results[universe_name] = {
            "top_etfs": top_etfs,
            "full_scores": full_scores,
            "window_results": window_results,
            "run_date": today
        }

    Path("results").mkdir(exist_ok=True)
    local_path = Path(f"results/bridge_{today}.json")
    with open(local_path, "w") as f:
        json.dump({"run_date": today, "universes": all_results}, f, indent=2)

    import push_results
    push_results.push_daily_result(local_path)
    print("\n=== Brownian Bridge Engine (multi‑window) complete ===")

if __name__ == "__main__":
    main()
