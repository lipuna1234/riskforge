"""CLI for local crypto strategy backtesting and paper simulation."""
import argparse
import json
from pathlib import Path

from .backtest import run_backtest
from .config import BacktestConfig
from .data import load_ohlcv_csv


def make_parser():
    parser = argparse.ArgumentParser(prog="riskforge", description="Risk-first spot strategy research (no live orders)")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("backtest", "paper"):
        current = sub.add_parser(command, help=f"Run a {command} simulation using OHLCV CSV")
        current.add_argument("--data", required=True, help="Path to OHLCV CSV file")
        current.add_argument("--strategy", choices=("ema", "rsi", "bollinger"), default="ema")
        current.add_argument("--cash", type=float, default=10_000.0)
        current.add_argument("--fee", type=float, default=0.001, help="Fee per side as decimal; 0.001 = 0.1%%")
        current.add_argument("--risk", type=float, default=0.01, help="Risk budget per trade; default 1%%")
        current.add_argument("--max-position", type=float, default=0.25, help="Maximum fraction of equity allocated")
        current.add_argument("--stop-loss", type=float, default=0.03, help="Stop loss distance; default 3%%")
        current.add_argument("--take-profit", type=float, default=0.06, help="Take profit distance; default 6%%")
        current.add_argument("--daily-loss-limit", type=float, default=0.03, help="Daily loss limit; default 3%%")
        current.add_argument("--output-dir", default="reports", help="Directory for CSV reports")
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    frame = load_ohlcv_csv(args.data)
    cfg = BacktestConfig(
        initial_cash=args.cash, fee_rate=args.fee, risk_per_trade=args.risk,
        max_position_fraction=args.max_position, stop_loss_fraction=args.stop_loss,
        take_profit_fraction=args.take_profit,
        daily_loss_limit_fraction=args.daily_loss_limit,
    )
    cfg.validate()
    metrics, trades, equity = run_backtest(frame, args.strategy, cfg)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trades_path = output_dir / f"{args.command}_{args.strategy}_trades.csv"
    equity_path = output_dir / f"{args.command}_{args.strategy}_equity.csv"
    trades.to_csv(trades_path, index=False)
    equity.to_csv(equity_path, index=False)
    print(json.dumps(metrics, indent=2))
    print(f"Trades report: {trades_path}")
    print(f"Equity report: {equity_path}")
    if args.command == "paper":
        print("PAPER MODE ONLY: no exchange connection and no orders were submitted.")


if __name__ == "__main__":
    main()
