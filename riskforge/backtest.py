"""Simple next-open, long-only spot backtester (educational, not execution-grade).

Signals for candle i are derived only from candle i-1 close or earlier.
Stops and targets use the current candle OHLC; when both hit in one candle,
the stop is assumed first because intrabar ordering cannot be inferred from OHLC.
"""
from dataclasses import dataclass, asdict

import pandas as pd

from .config import BacktestConfig
from .risk import DailyLossGuard, calculate_position_quantity
from .strategies import generate_signals


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    exit_reason: str


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    drawdown = (equity / peak) - 1.0
    return float(abs(drawdown.min()))


def run_backtest(frame: pd.DataFrame, strategy: str, config: BacktestConfig | None = None):
    config = config or BacktestConfig()
    config.validate()
    if len(frame) < 2:
        raise ValueError("At least two candles are required")
    # Decision known at prior candle's close; execute at this candle's open.
    signals = generate_signals(frame, strategy).shift(1, fill_value=False)
    cash = float(config.initial_cash)
    quantity = 0.0
    entry_price = 0.0
    entry_fee = 0.0
    entry_time = ""
    stop_price = 0.0
    take_price = 0.0
    trades: list[Trade] = []
    equity_points = []
    guard = DailyLossGuard(config.daily_loss_limit_fraction)
    day = None

    for i, candle in frame.iterrows():
        ts = pd.Timestamp(candle["timestamp"])
        this_day = ts.date()
        open_price = float(candle["open"])
        high = float(candle["high"])
        low = float(candle["low"])
        close = float(candle["close"])
        time_str = ts.isoformat()

        if day != this_day:
            day = this_day
            guard.new_day(max(0.0 + cash + quantity * open_price, 1e-12))

        if quantity > 0:
            exit_price = None
            exit_reason = ""
            # If a bar gaps past a stop/target, use its open as a conservative
            # proxy for the achievable fill in this simplified model.
            if open_price <= stop_price:
                exit_price, exit_reason = open_price, "stop_loss_gap"
            elif open_price >= take_price:
                exit_price, exit_reason = open_price, "take_profit_gap"
            elif low <= stop_price:
                exit_price, exit_reason = stop_price, "stop_loss"
            elif high >= take_price:
                exit_price, exit_reason = take_price, "take_profit"
            elif not bool(signals.iloc[i]):
                exit_price, exit_reason = open_price, "signal"
            if exit_price is not None:
                exit_fee = quantity * exit_price * config.fee_rate
                gross = quantity * (exit_price - entry_price)
                net = gross - entry_fee - exit_fee
                cash += quantity * exit_price - exit_fee
                trades.append(Trade(entry_time, time_str, entry_price, exit_price, quantity,
                                    gross, entry_fee + exit_fee, net, exit_reason))
                quantity = 0.0
                entry_price = entry_fee = stop_price = take_price = 0.0
                entry_time = ""

        # Risk guard is evaluated using equity before considering a new entry.
        current_equity = cash + quantity * close
        if guard.update(current_equity):
            can_enter = False
        else:
            can_enter = True

        if quantity == 0 and bool(signals.iloc[i]) and can_enter and i > 0 and cash > 0:
            equity_before = cash
            proposed_stop = open_price * (1 - config.stop_loss_fraction)
            qty = calculate_position_quantity(
                equity=equity_before,
                entry_price=open_price,
                stop_price=proposed_stop,
                fee_rate=config.fee_rate,
                risk_fraction=config.risk_per_trade,
                max_position_fraction=config.max_position_fraction,
            )
            affordable_qty = cash / (open_price * (1 + config.fee_rate))
            qty = min(qty, affordable_qty)
            if qty > 0:
                cost = qty * open_price
                entry_fee = cost * config.fee_rate
                cash -= cost + entry_fee
                quantity = qty
                entry_price = open_price
                entry_time = time_str
                stop_price = open_price * (1 - config.stop_loss_fraction)
                take_price = open_price * (1 + config.take_profit_fraction)

        equity = cash + quantity * close
        equity_points.append({"timestamp": ts, "equity": equity})
        guard.update(equity)

    # Mark remaining position to final close for a transparent end-of-data liquidation.
    if quantity > 0:
        candle = frame.iloc[-1]
        exit_price = float(candle["close"])
        exit_fee = quantity * exit_price * config.fee_rate
        gross = quantity * (exit_price - entry_price)
        net = gross - entry_fee - exit_fee
        cash += quantity * exit_price - exit_fee
        trades.append(Trade(entry_time, pd.Timestamp(candle["timestamp"]).isoformat(),
                            entry_price, exit_price, quantity, gross, entry_fee + exit_fee,
                            net, "end_of_data"))
        if equity_points:
            equity_points[-1]["equity"] = cash

    equity_frame = pd.DataFrame(equity_points)
    equity_series = equity_frame["equity"] if not equity_frame.empty else pd.Series(dtype=float)
    trade_frame = pd.DataFrame([asdict(trade) for trade in trades])
    final_equity = float(cash)
    metrics = {
        "strategy": strategy,
        "starting_equity": config.initial_cash,
        "ending_equity": final_equity,
        "net_return_pct": (final_equity / config.initial_cash - 1) * 100,
        "closed_trades": len(trades),
        "win_rate_pct": (sum(t.net_pnl > 0 for t in trades) / len(trades) * 100) if trades else 0.0,
        "max_drawdown_pct": max_drawdown(equity_series) * 100,
        "approx_total_fees": sum(t.fees for t in trades),
        "assumptions": "spot long-only; prior-close signal, next-open execution; fee model; simplified OHLC stop/target fills",
    }
    return metrics, trade_frame, equity_frame
