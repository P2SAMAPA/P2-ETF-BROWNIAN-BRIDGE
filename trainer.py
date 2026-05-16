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
        if prices.empty or len(prices) < config.ESTIMATION_WINDOW + 10:
            print("  Insufficient data")
            all_results[universe_name] = {"top_etfs": []}
            continue

        current_date = prices.index[-1]
        # Prepare market series if needed
        market_series = None
        if config.USE_MARKET_TARGET and config.TARGET_INDEX in prices.columns:
            market_series = prices[config.TARGET_INDEX].dropna()

        signals = {}
        full_details = {}

        for ticker in tickers:
            if ticker not in prices.columns:
                continue
            price_series = prices[ticker].dropna()
            if len(price_series) < config.ESTIMATION_WINDOW:
                continue
            result = compute_etf_signal(
                price_series, current_date,
                window=config.ESTIMATION_WINDOW,
                bridge_type=config.BRIDGE_TYPE,
                use_market_target=config.USE_MARKET_TARGET,
                market_series=market_series
            )
            if result is None:
                continue
            signals[ticker] = result["signal"]
            full_details[ticker] = result

        if not signals:
            print("  No valid signals")
            all_results[universe_name] = {"top_etfs": []}
            continue

        sorted_etfs = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_etfs = []
        full_scores = {}
        for ticker, sig in sorted_etfs[:config.TOP_N]:
            top_etfs.append({"ticker": ticker, "signal": float(sig)})
            full_scores[ticker] = float(sig)
        print(f"  Top 3 ETFs by bridge signal: {[e['ticker'] for e in top_etfs]}")
        all_results[universe_name] = {
            "top_etfs": top_etfs,
            "full_scores": full_scores,
            "details": full_details,
            "run_date": today
        }

    Path("results").mkdir(exist_ok=True)
    local_path = Path(f"results/bridge_{today}.json")
    with open(local_path, "w") as f:
        json.dump({"run_date": today, "universes": all_results}, f, indent=2)

    import push_results
    push_results.push_daily_result(local_path)
    print("\n=== Geometric Brownian Bridge Engine complete ===")

if __name__ == "__main__":
    main()
