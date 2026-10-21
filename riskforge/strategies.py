"""Long-only starter strategy signal generation.

A signal value of 1 means enter/hold long; 0 means exit/stay in cash.
Signals are based on candle close. The backtester executes them on the next open.
"""
import pandas as pd

from .indicators import bollinger_bands, ema, rsi

STRATEGIES = ("ema", "rsi", "bollinger")


def generate_signals(frame: pd.DataFrame, strategy: str) -> pd.Series:
    close = frame["close"].astype(float)
    strategy = strategy.lower()
    if strategy == "ema":
        fast = ema(close, 12)
        slow = ema(close, 26)
        signal = fast > slow
    elif strategy == "rsi":
        strength = rsi(close, 14)
        # Entry on oversold conditions; remain long until recovery threshold.
        signal_values = []
        in_position = False
        for value in strength:
            if pd.isna(value):
                signal_values.append(False)
                continue
            if not in_position and value < 30:
                in_position = True
            elif in_position and value > 50:
                in_position = False
            signal_values.append(in_position)
        signal = pd.Series(signal_values, index=frame.index, dtype=bool)
    elif strategy == "bollinger":
        lower, middle, _upper = bollinger_bands(close, 20, 2.0)
        signal_values = []
        in_position = False
        for price, low_band, mid_band in zip(close, lower, middle):
            if pd.isna(low_band) or pd.isna(mid_band):
                signal_values.append(False)
                continue
            if not in_position and price < low_band:
                in_position = True
            elif in_position and price >= mid_band:
                in_position = False
            signal_values.append(in_position)
        signal = pd.Series(signal_values, index=frame.index, dtype=bool)
    else:
        raise ValueError(f"Unknown strategy {strategy!r}. Choose one of {STRATEGIES}.")
    return signal.fillna(False).astype(bool)
