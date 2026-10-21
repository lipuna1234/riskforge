"""Configuration models and validation helpers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    fee_rate: float = 0.001
    risk_per_trade: float = 0.01
    max_position_fraction: float = 0.25
    stop_loss_fraction: float = 0.03
    take_profit_fraction: float = 0.06
    daily_loss_limit_fraction: float = 0.03

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if not 0 <= self.fee_rate < 0.1:
            raise ValueError("fee_rate must be between 0 and 0.1")
        if not 0 < self.risk_per_trade <= 0.05:
            raise ValueError("risk_per_trade must be in (0, 0.05]")
        if not 0 < self.max_position_fraction <= 1:
            raise ValueError("max_position_fraction must be in (0, 1]")
        if not 0 < self.stop_loss_fraction < 1:
            raise ValueError("stop_loss_fraction must be in (0, 1)")
        if not 0 < self.take_profit_fraction < 5:
            raise ValueError("take_profit_fraction must be in (0, 5)")
        if not 0 < self.daily_loss_limit_fraction <= 0.2:
            raise ValueError("daily_loss_limit_fraction must be in (0, 0.2]")
