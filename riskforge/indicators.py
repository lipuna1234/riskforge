"""Small dependency-light technical indicator implementations."""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    if period < 1:
        raise ValueError("period must be >= 1")
    return series.astype(float).ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    if period < 2:
        raise ValueError("period must be >= 2")
    delta = series.astype(float).diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    out = out.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    out = out.mask((avg_gain == 0) & (avg_loss == 0), 50.0)
    return out


def bollinger_bands(series: pd.Series, period: int = 20, deviations: float = 2.0):
    if period < 2 or deviations <= 0:
        raise ValueError("period must be >= 2 and deviations must be positive")
    rolling = series.astype(float).rolling(window=period, min_periods=period)
    middle = rolling.mean()
    std = rolling.std(ddof=0)
    return middle - deviations * std, middle, middle + deviations * std
