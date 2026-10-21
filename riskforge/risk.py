"""Risk calculations used by the backtest and paper-trading utilities."""
from dataclasses import dataclass


@dataclass
class DailyLossGuard:
    """Stops permitting new entries after a day breaches its starting-equity limit."""
    limit_fraction: float = 0.03
    day_start_equity: float | None = None
    halted: bool = False

    def __post_init__(self):
        if not 0 < self.limit_fraction <= 0.2:
            raise ValueError("limit_fraction must be in (0, 0.2]")

    def new_day(self, equity: float) -> None:
        if equity <= 0:
            raise ValueError("equity must be positive")
        self.day_start_equity = equity
        self.halted = False

    def update(self, equity: float) -> bool:
        if self.day_start_equity is None:
            self.new_day(equity)
        if equity <= self.day_start_equity * (1 - self.limit_fraction):
            self.halted = True
        return self.halted


def calculate_position_quantity(
    equity: float,
    entry_price: float,
    stop_price: float,
    fee_rate: float = 0.001,
    risk_fraction: float = 0.01,
    max_position_fraction: float = 0.25,
) -> float:
    """Return quantity capped by risk budget and notional cap, including fee approximation."""
    if equity <= 0 or entry_price <= 0 or stop_price <= 0:
        raise ValueError("equity and prices must be positive")
    if stop_price >= entry_price:
        raise ValueError("stop_price must be below entry_price for a long spot trade")
    if not 0 <= fee_rate < 0.1:
        raise ValueError("fee_rate must be between 0 and 0.1")
    if not 0 < risk_fraction <= 0.05:
        raise ValueError("risk_fraction must be in (0, 0.05]")
    if not 0 < max_position_fraction <= 1:
        raise ValueError("max_position_fraction must be in (0, 1]")
    loss_per_unit = (entry_price - stop_price) + fee_rate * (entry_price + stop_price)
    if loss_per_unit <= 0:
        return 0.0
    risk_quantity = (equity * risk_fraction) / loss_per_unit
    notional_quantity = (equity * max_position_fraction) / (entry_price * (1 + fee_rate))
    return max(0.0, min(risk_quantity, notional_quantity))
