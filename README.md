# RiskForge — Risk-First Crypto Trading Lab

RiskForge is an educational Python project for researching crypto spot strategies with **historical backtesting and paper trading first**. It is designed around risk controls, reproducibility, and transparent results—not promises of profit.

> **Important risk notice:** Cryptocurrency trading can lose money. Backtests can overfit and paper fills do not reproduce real-world slippage, liquidity, outages, or emotional decisions. This project does not guarantee returns and is not financial advice. The initial version intentionally does **not** submit live orders.

## What is included

- **Spot-only research**: no futures, margin, borrowing, or leverage.
- **Three strategies to compare**: EMA trend, RSI mean reversion, and Bollinger Bands mean reversion.
- **Fee-aware backtest**: applies configurable fees on entries/exits and models a simple stop-loss/take-profit rule.
- **Risk controls**: position-size cap, risk-per-trade cap, daily loss limit, and maximum drawdown reporting.
- **Paper trader**: simulates decisions on historical OHLCV candles; no private API key is required.
- **Data validation**: checks required OHLCV fields, timestamps, and missing values.
- **Unit tests and Docker**: repeatable local development.
- **No secrets in Git**: credentials should never be committed.

## Project layout

```text
riskforge/
├── riskforge/
│   ├── __init__.py
│   ├── cli.py             # command-line interface
│   ├── config.py          # validated configuration
│   ├── data.py            # OHLCV CSV loading and checks
│   ├── indicators.py      # EMA, RSI, Bollinger Bands
│   ├── strategies.py      # independent strategy signals
│   ├── backtest.py        # long-only, fee-aware simulation
│   └── risk.py            # sizing and risk limit helpers
├── tests/
│   ├── test_indicators.py
│   ├── test_risk.py
│   └── test_backtest.py
├── data/
│   └── sample_btcusdt.csv # small illustrative dataset
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 1. Requirements

- Python 3.11 or newer
- Git
- Optional: Docker Desktop

All commands below assume a terminal opened in the cloned repository directory.

## 2. Download the project

```bash
git clone https://github.com/lipuna1234/riskforge.git
cd riskforge
```

### Windows PowerShell: create and activate a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

If PowerShell blocks activation, use this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 3. Run tests before trading research

```bash
pytest -q
```

Tests validate the basic indicator calculations, risk calculations, and backtest behavior. A passing test suite is not evidence that a strategy is profitable.

## 4. Run the sample backtest

Use the included small illustrative BTC/USDT dataset:

```bash
python -m riskforge.cli backtest --data data/sample_btcusdt.csv --strategy ema
```

Compare the three strategies independently:

```bash
python -m riskforge.cli backtest --data data/sample_btcusdt.csv --strategy ema
python -m riskforge.cli backtest --data data/sample_btcusdt.csv --strategy rsi
python -m riskforge.cli backtest --data data/sample_btcusdt.csv --strategy bollinger
```

The included data is **synthetic/illustrative**, not exchange history. Replace it with properly obtained historical candles before making any research conclusions.

The program reports ending equity, net return, number of closed trades, win rate, maximum drawdown, and approximate fees. Returns are not forecasts.

## 5. Prepare historical OHLCV data

Create a CSV file with these columns:

```csv
timestamp,open,high,low,close,volume
2025-01-01T00:00:00Z,94000,94500,93600,94200,100.0
2025-01-01T01:00:00Z,94200,94900,94000,94700,125.0
```

Use chronological candles at a consistent interval. Numeric columns must be finite, prices must be positive, high must be at least open/close/low, low must be at most open/close/high, and timestamps must be valid and increasing. Never mix intervals or symbols in one file.

If using exchange data, check the exchange's current API terms and market-data documentation. Public historical candle data does not require placing orders. Keep private trading permissions disabled during research.

## 6. Strategy overview

### EMA trend-following
Generates a long entry when the short EMA is above the long EMA and an exit when it is not. Moving averages lag and may suffer repeated losses in sideways markets.

### RSI mean reversion
Buys after RSI reaches an oversold region and exits when RSI reaches a recovery threshold. An asset can remain oversold while continuing to fall.

### Bollinger Bands mean reversion
Buys when price closes below the lower band and exits when price returns toward the middle band. Strong trends can cause extended losses.

These are starter hypotheses, not a claim that any one of them is best. Evaluate each separately and use out-of-sample data.

## 7. Risk controls and assumptions

Default backtest assumptions are intentionally conservative in spirit but still simplified:

- Starting cash: configured in the CLI.
- No leverage; long-only spot positions.
- Entry and exit fees are charged against traded notional.
- One position at a time.
- Position allocation is capped.
- Stop-loss and take-profit are evaluated against candle OHLC. If a candle opens beyond a stop or target, the simulator uses the open as an approximate gap fill; if both levels are touched inside a candle, the stop-loss triggers first because intrabar ordering is unknown.
- Signals are generated from candle closes and acted on at the next candle open to avoid same-candle look-ahead.
- Gap risk and slippage are not fully modeled; add realistic slippage assumptions before interpreting results.
- The daily loss guard blocks new entries after observed equity reaches its configured daily threshold; it cannot guarantee a maximum loss because of gaps, open positions, candle granularity, or software/data failures.

A risk limit cannot make a strategy safe or guarantee that losses remain within the chosen amount.

## 8. Paper trading

The starter paper mode processes a CSV candle file and simulates decisions without sending orders:

```bash
python -m riskforge.cli paper --data data/sample_btcusdt.csv --strategy ema
```

Paper trading is a **simulation**. Do not interpret it as a successful live exchange integration. The current project does not create Binance orders and does not need Binance API credentials.

A future exchange-data adapter should be read-only by default, store credentials outside the repository, handle rate limits and outages, and be tested independently before considering any order execution.

## 9. Configure parameters

See `riskforge/cli.py --help` and the options on each command. Examples:

```bash
python -m riskforge.cli backtest --help
python -m riskforge.cli paper --help
```

Always record strategy parameters, trading pair, interval, date range, fee assumptions, and data source with each result. Do not optimize on the same time period used to report final performance.

## 10. Docker

Build the image:

```bash
docker build -t riskforge:local .
```

Run unit tests in Docker:

```bash
docker compose run --rm riskforge pytest -q
```

Run a backtest in Docker:

```bash
docker compose run --rm riskforge python -m riskforge.cli backtest --data data/sample_btcusdt.csv --strategy ema
```

## 11. Environment variables and API keys

`.env.example` documents safe placeholder settings only. The current version does not read keys or place live orders.

**Never commit** exchange API keys, secrets, seed phrases, wallet private keys, tokens, or account information. If you later add exchange access, create restricted keys with withdrawals disabled; start with read-only permissions and IP restrictions where supported. Use a secret manager or local environment configuration excluded by `.gitignore`. If a key is ever committed or shared, revoke it immediately.

## 12. How to evaluate a strategy responsibly

1. Verify candle quality and timestamps.
2. Define the strategy and parameters before testing.
3. Include fees and realistic slippage.
4. Separate chronological training, validation, and out-of-sample periods.
5. Compare against buy-and-hold and a no-trade baseline.
6. Review trade count, drawdown, average win/loss, exposure, fees, and behavior in different market regimes.
7. Use walk-forward testing and avoid selecting a strategy solely because it had the highest historical return.
8. Run a long paper-trading period before considering any live deployment.

Small samples can create misleading performance statistics. A high historical return alone is not enough.

## 13. Troubleshooting

- **`python` not found on Windows:** use `py -3.11` and confirm Python is installed.
- **Wrong environment:** activate `.venv`, then run `python -m pip --version`.
- **Missing package:** run `pip install -r requirements-dev.txt`.
- **CSV rejected:** check column names, ISO timestamps, numeric values, and chronological order.
- **No trades:** the chosen strategy may have no entry signals on the provided data. That is expected; do not change parameters just to force trades.
- **Different results from other tools:** confirm candles, timezone, indicator warm-up, fees, fill assumptions, and stop order are identical.

## Roadmap

- [x] Modular strategy and indicator code
- [x] CSV validation and local backtest
- [x] Paper simulation without order submission
- [x] Basic risk helpers and unit tests
- [x] Docker development environment
- [ ] Exchange historical data adapter with rate-limit handling
- [ ] Robust slippage and gap simulation
- [ ] Walk-forward and Monte Carlo analysis
- [ ] Optional read-only market-data integration

## Disclaimer

RiskForge is software for education and research. It is not investment advice, does not guarantee profit, and can contain bugs or simplified assumptions. You are responsible for verifying the code, data, exchange terms, legal/tax obligations, and any decisions made from its output. Live trading is intentionally disabled in this version.
