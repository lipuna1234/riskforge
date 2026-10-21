"""Paper-only five-slot Binance USD-M futures backtest. Never places orders.

Defaults: 5 slots x INR 10,000 virtual margin, 3x leverage, +3%/-1%
underlying-price TP/SL. P&L is an illustrative INR-equivalent model, not
actual account P&L; funding, liquidation and exact contract sizing are omitted.
"""
import argparse
import os
import time
import pandas as pd
import requests

SLOTS = [
    ("slot1_ema_btc", "BTCUSDT", "ema"),
    ("slot2_meanrev_eth", "ETHUSDT", "meanrev"),
    ("slot3_breakout_btc", "BTCUSDT", "breakout"),
    ("slot4_pullback_eth", "ETHUSDT", "pullback"),
    ("slot5_ema_eth", "ETHUSDT", "ema"),
]
BASE = "https://fapi.binance.com"


def fetch(symbol, interval, days):
    end = int(time.time() * 1000)
    start = end - days * 86400000
    rows = []
    while start < end:
        r = requests.get(BASE + "/fapi/v1/klines", params={
            "symbol": symbol, "interval": interval, "startTime": start,
            "endTime": end, "limit": 1500}, timeout=20)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        new_start = int(batch[-1][0]) + 1
        if new_start <= start:
            break
        start = new_start
        time.sleep(.1)
    if not rows:
        raise RuntimeError("No candles returned; verify symbol and interval.")
    cols = ["open_time","open","high","low","close","volume","close_time",
            "qv","trades","tb","tq","ignore"]
    d = pd.DataFrame(rows, columns=cols)
    for c in ("open","high","low","close","volume","close_time"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["time"] = pd.to_datetime(d.open_time, unit="ms", utc=True)
    d = d.drop_duplicates("time").sort_values("time").set_index("time")
    d = d[d.close_time < int(time.time() * 1000)]
    return d[["open","high","low","close","volume"]].dropna()


def features(d):
    x = d.copy()
    x["e20"] = x.close.ewm(span=20, adjust=False).mean()
    x["e50"] = x.close.ewm(span=50, adjust=False).mean()
    delta = x.close.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    x["rsi"] = 100 - 100 / (1 + up / dn.replace(0, float("nan")))
    x["mid"] = x.close.rolling(20).mean()
    sd = x.close.rolling(20).std(ddof=0)
    x["upper"], x["lower"] = x.mid + 2*sd, x.mid - 2*sd
    x["vavg"] = x.volume.rolling(20).mean()
    x["rh"] = x.high.shift().rolling(20).max()
    x["rl"] = x.low.shift().rolling(20).min()
    return x.dropna()


def signal(r, p, strat):
    if strat == "ema":
        if r.e20 > r.e50 and r.close > r.e20 and r.rsi > 52: return "LONG"
        if r.e20 < r.e50 and r.close < r.e20 and r.rsi < 48: return "SHORT"
    elif strat == "meanrev":
        if p.close < p.lower and r.close > r.lower and r.rsi < 45: return "LONG"
        if p.close > p.upper and r.close < r.upper and r.rsi > 55: return "SHORT"
    elif strat == "breakout":
        if r.close > r.rh and r.volume > 1.2*r.vavg and r.rsi > 52: return "LONG"
        if r.close < r.rl and r.volume > 1.2*r.vavg and r.rsi < 48: return "SHORT"
    elif strat == "pullback":
        if r.e20 > r.e50 and r.low <= r.e20 and r.close > r.e20 and r.rsi > 50: return "LONG"
        if r.e20 < r.e50 and r.high >= r.e20 and r.close < r.e20 and r.rsi < 50: return "SHORT"
    return None


def simulate(d, slot, margin, leverage, tp, sl, fee, slip):
    x = features(d)
    equity, pos, trades = float(margin), None, []
    for i in range(1, len(x)-1):
        r, p = x.iloc[i], x.iloc[i-1]
        if pos:
            out = reason = None
            if pos["side"] == "LONG":
                if r.low <= pos["stop"]: out, reason = pos["stop"], "STOP"
                elif r.high >= pos["target"]: out, reason = pos["target"], "TAKE_PROFIT"
            else:
                if r.high >= pos["stop"]: out, reason = pos["stop"], "STOP"
                elif r.low <= pos["target"]: out, reason = pos["target"], "TAKE_PROFIT"
            if out is not None:
                direction = 1 if pos["side"] == "LONG" else -1
                px = out * (1-slip if direction == 1 else 1+slip)
                gross = direction * (px-pos["entry"]) / pos["entry"] * pos["notional"]
                costs = pos["notional"] * fee * 2 + pos["notional"] * slip
                net = gross - costs
                equity += net
                trades.append({"slot":slot[0],"symbol":slot[1],"strategy":slot[2],
                    "side":pos["side"],"entry_time":pos["time"],"exit_time":r.name,
                    "entry":pos["entry"],"exit":px,"notional_inr_equivalent":pos["notional"],
                    "net_pnl_inr_equivalent":net,"exit_reason":reason,"equity_after":equity})
                pos = None
        if pos is None:
            side = signal(r, p, slot[2])
            if side:
                direction = 1 if side == "LONG" else -1
                raw = float(x.iloc[i+1].open)
                entry = raw * (1+slip if direction == 1 else 1-slip)
                notional = max(equity, 0) * leverage
                if notional <= 0: continue
                pos = {"side":side,"entry":entry,"notional":notional,"time":x.index[i+1],
                    "stop":entry*(1-sl if direction == 1 else 1+sl),
                    "target":entry*(1+tp if direction == 1 else 1-tp)}
    t = pd.DataFrame(trades)
    if t.empty:
        return {"slot":slot[0],"symbol":slot[1],"strategy":slot[2],"trades":0,
                "win_rate_pct":0,"net_pnl_inr_equivalent":0,"ending_equity_inr_equivalent":margin}, t
    wins = t[t.net_pnl_inr_equivalent > 0]
    losses = t[t.net_pnl_inr_equivalent < 0]
    gw = wins.net_pnl_inr_equivalent.sum()
    gl = abs(losses.net_pnl_inr_equivalent.sum())
    return {"slot":slot[0],"symbol":slot[1],"strategy":slot[2],"trades":len(t),
        "win_rate_pct":round(100*len(wins)/len(t),2),
        "net_pnl_inr_equivalent":round(float(t.net_pnl_inr_equivalent.sum()),2),
        "ending_equity_inr_equivalent":round(float(margin+t.net_pnl_inr_equivalent.sum()),2),
        "profit_factor":round(float(gw/gl),3) if gl else "inf"}, t


def backtest(a):
    os.makedirs(a.output, exist_ok=True)
    data, summaries, trades = {}, [], []
    for slot in SLOTS:
        if slot[1] not in data:
            print("Fetching", slot[1], a.days, "days of", a.interval, "futures candles")
            data[slot[1]] = fetch(slot[1], a.interval, a.days)
        summary, t = simulate(data[slot[1]], slot, a.capital_per_slot, a.leverage,
                              a.tp, a.sl, a.fee, a.slippage)
        summaries.append(summary)
        if not t.empty: trades.append(t)
    pd.DataFrame(summaries).to_csv(os.path.join(a.output,"futures_slot_summary.csv"),index=False)
    (pd.concat(trades,ignore_index=True) if trades else pd.DataFrame()).to_csv(
        os.path.join(a.output,"futures_all_trades.csv"),index=False)
    print(pd.DataFrame(summaries).to_string(index=False))
    print("Virtual margin total: INR", a.capital_per_slot*len(SLOTS))
    print("WARNING: simplified INR-equivalent simulation; funding, liquidation, FX conversion and exact contract rules omitted.")


def monitor(a):
    print("Paper signal monitor only: no orders. Ctrl+C to stop.")
    while True:
        try:
            cache = {}
            for slot in SLOTS:
                if slot[1] not in cache: cache[slot[1]] = features(fetch(slot[1],a.interval,10))
                x=cache[slot[1]]
                print(slot[0],slot[1],signal(x.iloc[-1],x.iloc[-2],slot[2]) or "NO SIGNAL",
                      "TP",a.tp*100,"% SL",a.sl*100,"%")
            time.sleep(max(30, {"m":60,"h":3600,"d":86400}[a.interval[-1]]*int(a.interval[:-1])))
        except KeyboardInterrupt: return
        except Exception as e:
            print("Data error:",e); time.sleep(30)


def main():
    p=argparse.ArgumentParser(description="RiskForge futures paper research only")
    sub=p.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("futures-backtest")
    b.add_argument("--days",type=int,default=90); b.add_argument("--interval",default="5m")
    b.add_argument("--capital-per-slot",type=float,default=10000); b.add_argument("--leverage",type=float,default=3)
    b.add_argument("--tp",type=float,default=.03); b.add_argument("--sl",type=float,default=.01)
    b.add_argument("--fee",type=float,default=.0005); b.add_argument("--slippage",type=float,default=.0005)
    b.add_argument("--output",default="reports"); b.set_defaults(func=backtest)
    m=sub.add_parser("futures-paper"); m.add_argument("--interval",default="5m")
    m.add_argument("--tp",type=float,default=.03); m.add_argument("--sl",type=float,default=.01); m.set_defaults(func=monitor)
    a=p.parse_args(); a.func(a)

if __name__ == "__main__": main()
