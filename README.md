# Geometric Brownian Bridge Engine

Models ETF returns as Brownian bridges conditioned on end‑of‑month targets.  
The required drift to hit the target (price or volatility) gives a directional signal.

- **Price bridge:** target = ETF's own price at last month‑end (or market index)
- **Volatility bridge:** target = long‑term mean volatility
- **Signal:** annualised drift (positive = bullish)
- **Output:** top 3 ETFs per universe by signal strength, plus full ranking

Runs daily on GitHub Actions.

## Local execution

```bash
pip install -r requirements.txt
export HF_TOKEN=<your_token>
python trainer.py
streamlit run streamlit_app.py
