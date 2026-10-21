"""Load and validate OHLCV candle CSV files."""
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    result = frame.loc[:, REQUIRED_COLUMNS].copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    if result["timestamp"].isna().any():
        raise ValueError("Every timestamp must be parseable as a date/time")
    if result["timestamp"].duplicated().any():
        raise ValueError("Timestamps must be unique")
    if not result["timestamp"].is_monotonic_increasing:
        raise ValueError("Rows must be sorted by timestamp in ascending order")
    for column in ("open", "high", "low", "close", "volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    values = result[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("OHLCV values must be finite numeric values")
    if (result[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if (result["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    if (result["high"] < result[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("High must be >= open, close, and low")
    if (result["low"] > result[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Low must be <= open, close, and high")
    return result.reset_index(drop=True)


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"CSV file not found: {source}")
    return validate_ohlcv(pd.read_csv(source))
