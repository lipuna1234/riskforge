import pandas as pd

from riskforge.backtest import run_backtest
from riskforge.config import BacktestConfig
from riskforge.data import validate_ohlcv


def sample_frame():
    close = [100 + i * 0.2 for i in range(80)] + [116 - i * 0.5 for i in range(20)]
    rows = []
    ts = pd.date_range("2025-01-01", periods=len(close), freq="h", tz="UTC")
    previous = close[0]
    for stamp, price in zip(ts, close):
        rows.append({"timestamp": stamp, "open": previous, "high": max(previous, price) * 1.002,
                     "low": min(previous, price) * 0.998, "close": price, "volume": 10})
        previous = price
    return validate_ohlcv(pd.DataFrame(rows))


def test_backtest_returns_metrics_and_frames():
    metrics, trades, equity = run_backtest(sample_frame(), "ema", BacktestConfig())
    assert metrics["starting_equity"] == 10_000
    assert metrics["ending_equity"] > 0
    assert "net_pnl" in trades.columns or trades.empty
    assert len(equity) == 100


def test_unknown_strategy_raises():
    import pytest
    with pytest.raises(ValueError):
        run_backtest(sample_frame(), "not-a-strategy")
