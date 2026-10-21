import pandas as pd

from riskforge.indicators import bollinger_bands, ema, rsi


def test_ema_returns_nan_during_warmup():
    values = ema(pd.Series([1, 2, 3, 4, 5], dtype=float), 3)
    assert values.iloc[:2].isna().all()
    assert values.iloc[2:].notna().all()


def test_rsi_is_between_zero_and_one_hundred():
    values = rsi(pd.Series(range(1, 50), dtype=float), 14).dropna()
    assert ((values >= 0) & (values <= 100)).all()


def test_bollinger_bands_order():
    lower, middle, upper = bollinger_bands(pd.Series(range(1, 30), dtype=float), 5)
    valid = lower.notna()
    assert (lower[valid] <= middle[valid]).all()
    assert (middle[valid] <= upper[valid]).all()
