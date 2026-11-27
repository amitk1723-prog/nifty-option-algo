# -*- coding: utf-8 -*-
"""
nifty_option_pro_v28_FULL.py
============================
Ek hi file me DONO cheezein:
  (A) NIFTY OPTION SIGNAL PRO v28 BOT  - Dhan/Upstox live algo, backtest, Final Buy (blue arrow),
      real-trade journal CSV, Telegram alert, manual exit, strike/expiry/exit selector menu.
  (B) nifty_dash DASHBOARD            - Pine jaise saare 12 tables (SIGNAL, LOG, BREADTH, OI, STOCKS,
      SECTOR, SECTOR ALL, JOURNAL, PHASE, EXTRA STATS, GRADE, VOL PCR) + candle chart
      (BUY/EXIT/FINAL BUY marker, Entry/SL/T1/T2, Reversal, Call/Put Wall) -> dashboard.html
"""
import os
import time
import math
import datetime as dt
import pytz
import requests
import pandas as pd
import numpy as np
import json
import traceback
from types import SimpleNamespace

# ==============================================================================
# 1. BROKER, CHART, EXECUTION & TELEGRAM CONFIG
# ==============================================================================
CONFIG = {
    "BROKER": os.environ.get("BROKER", "DHAN"),
    "CHART_SYMBOL": os.environ.get("CHART_SYMBOL", "NIFTY_SPOT"),
    "DHAN_CLIENT_ID": os.environ.get("DHAN_CLIENT_ID", "YOUR_DHAN_CLIENT_ID"),
    "DHAN_ACCESS_TOKEN": os.environ.get("DHAN_ACCESS_TOKEN", "YOUR_DHAN_ACCESS_TOKEN"),
    "UPSTOX_ACCESS_TOKEN": os.environ.get("UPSTOX_ACCESS_TOKEN", "YOUR_UPSTOX_ACCESS_TOKEN"),
    "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "RUN_MODE": "LIVE",
    "BACKTEST_DAYS": 30,
    "BACKTEST_ENTRY_TYPE": "BOTH",
    "AUTO_PLACE_ORDER": False,
    "PRODUCT_TYPE": "INTRADAY",
    "INTERACTIVE_MENU": True,
    "REAL_TRADES_CSV": "live_real_trades_journal.csv",
    "DASH_ON": True,
    "DASH_HTML_PATH": "dashboard.html",
    "DASH_CONSOLE_TABLES": False,

    # --- PAPER TRADING (LIVE market me virtual orders, real option LTP par fill) ---
    "PAPER_TRADING": os.environ.get("PAPER_TRADING", "0") == "1",
    "PAPER_CAPITAL": 100000.0,
    "PAPER_BROKERAGE_PER_ORDER": 20.0,
    "PAPER_SLIPPAGE_PTS": 0.0,
    "PAPER_ORDERS_CSV": "paper_orders_log.csv",
    "PAPER_TRADES_CSV": "paper_trades_journal.csv",
    "PAPER_STATE_JSON": "paper_open_positions.json",

    # --- OPTION PREMIUM (Rs) TRACKING: backtest me real/estimate option price ---
    "BT_USE_ROLLING_API": True,   # expired contract ke liye Dhan Rolling Option API (best-effort)
    "BT_ROLLING_OFFSETS": 4,      # rolling API me ATM-4 .. ATM+4 tak strikes mangwa kar locked strike dhundhna
    "BT_RISK_FREE": 0.07,         # Black-Scholes fallback ke liye
}

# ==============================================================================
# 2. COMPLETE INDICATOR SETTINGS (100% EXACT PINE SCRIPT v28 + VOL PCR)
# ==============================================================================
PARAMS = {
    # --- STRIKE & EXPIRY SELECTION OPTIONS ---
    "strikeMode": "ATM",
    "expiryMode": "CURRENT_WEEK",
    "manualExpiry": "",

    # --- TARGET EXIT OPTIONS ---
    "exitMode": "T1",
    "t1ExitPct": 50,
    "useHighLowForTarget": True,

    # --- G0: Chart, Market Window & Trade Settings ---
    "chartType": "Index/Fut",
    "optStep": 50.0,
    "optLot": 65,
    "optDelta": 0.5,
    "slMult": 1.5,
    "rrT": 2.0,
    "capital": 100000.0,
    "riskPct": 1.0,
    "needN": 4,
    "orBars": 3,
    "sess_start": "09:20",
    "sess_end": "15:00",
    "extMult": 3.0,
    "coolBars": 6,

    # MTF Toggles (3m, 5m, 15m, 1h, 4h)
    "mtfOn": True,
    "mtf15Req": False,
    "mtfNeed": 3,

    # Sideways & DI Filter Toggles
    "adxOn": True,
    "adxLen": 14,
    "adxMin": 20.0,
    "diOn": True,
    "diMtf": True,
    "diNeed": 2,
    "adxTrd": 20.0,
    "diStrong": 20.0,
    "diWeak": 20.0,

    # Direction & PE Specific Filters
    "allowCE": True,
    "allowPE": True,
    "peBrMax": 100.0,
    "peAdxMin": 0.0,
    "peHtf": "1h PE",
    "peBelowOpen": True,
    "optSym": "",
    "optEntry": 0.0,

    # --- G5: Final Buy (Green/Red Arrow -> Calculation -> Blue Arrow) ---
    "wfOn": True,
    "wfMin": 1,
    "wfRule": "E",
    "wfA": 0.5,
    "wfDip": 0.5,
    "wfWk": 40,
    "wfF": 3,
    "wfS": 5,
    "wfMax": 20,
    "wfUp": 0.5,
    "wfUpPts": 0.0,
    "wfWick": True,

    # --- G7: Daily 20MA Direction Gate (7 din / 5 din) ---
    "dgOn": True,
    "dgMode": "Sirf PE par",
    "peScMin": 3,
    "dgLen": 20,
    "dgD1": 7,
    "dgD2": 5,
    "dgFlat": 0.05,

    # --- G8: v22 Upgrades ---
    "lateOn": False,
    "lateAdx": 40.0,
    "lateBr": 90.0,
    "arOn": False,
    "arN": 3,
    "rsiOn": False,
    "rsiHi": 76.0,
    "rsiLo": 24.0,
    "cdOn": False,
    "cdPos": 0.6,
    "vfOn": False,
    "vfMult": 1.0,
    "lvlOn": False,
    "lvlBuf": 0.15,
    "rdOn": False,
    "rdStep": 100.0,
    "rdPts": 15.0,
    "opOn": False,
    "vxOn": False,
    "vxLook": 12,
    "tmOn": False,
    "tmS1": ("09:20", "09:35"),
    "tmS2": ("12:00", "13:30"),
    "tmS3": ("14:45", "15:00"),
    "exOn": False,
    "exDay": "Tuesday",
    "beOn": False,
    "beR": 1.0,
    "beLock": 0.1,
    "trOn": False,
    "gdA": 8,
    "gdB": 6,

    # --- G3, G4, G9: OPTION OI + OPTION VOLUME PCR + FUTURES OI ---
    "autoOc": True,
    "ocN": 4,
    "pcrIn": 0.0,
    "callWall": 0.0,
    "putWall": 0.0,
    "wallBuf": 0.3,
    "pcrBull": 1.1,
    "pcrBear": 0.9,

    "ovOn": True,
    "ovN": 5,
    "ovBull": 1.2,
    "ovBear": 0.8,
    "ovFeed": True,

    "futOiOn": True,
    "oiLook": 12,

    "oiProbFilterOn": True,
    "minOiProbCE": 55.0,
    "minOiProbPE": 55.0,
    "requireHighProbOnly": False,

    # --- G1: Pre-Alert & Display ---
    "preSec": 15,

    # --- G2: Breadth (20 Heavyweight Stocks) ---
    "flatPct": 0.02,
    "implRef": 0.5,
    "hiTh": 65.0,

    # --- GSC: v28 Sector Strength ---
    "scOn": True,
    "scTh": 0.25,
    "scFeed": False,
    "scNeed": 2,
    "scBankOk": True,
}

# ==============================================================================
# 2B. DASHBOARD DISPLAY SETTINGS
# ==============================================================================
_dd = dt.date.today()
DASH = {
    "textSz": "tiny",
    "showDetail": True,
    "showMk": True,
    "lblMode": "ON",
    "lblBars": 0,
    "wfArrow": True,
    "wfMaShow": False,
    "posSig": "Top Right", "posLg": "Bottom Right", "posBr": "Top Left", "posOi": "Middle Left",
    "posLs": "Bottom Left", "scPos": "Top Center", "scPosA": "Middle Right", "posJ": "Bottom Center",
    "posPh": "Bottom Center", "posXs": "Middle Right", "gdPos": "Top Center", "vp_pos": "Middle Left",
    "showLog": True, "showList": True, "scAll": True, "jShow": True, "phShow": True,
    "xsShow": True, "gdShow": True, "vp_showTbl": True,
    "jPg": 1,
    "vp_useSpot": True,
    "ph1S": (_dd - dt.timedelta(days=60)).isoformat(),
    "ph2S": (_dd - dt.timedelta(days=30)).isoformat(),
    "phE": _dd.isoformat(),
}

def clamp_strike_span(n: int) -> int:
    return max(2, min(9, int(n)))

def get_trade_strike(spot_price: float, side: str) -> float:
    step = PARAMS["optStep"]
    atm = round(spot_price / step) * step
    mode = PARAMS["strikeMode"].upper()
    if mode == "ITM_1":
        return (atm - step) if side == "CE" else (atm + step)
    elif mode == "ITM_2":
        return (atm - 2 * step) if side == "CE" else (atm + 2 * step)
    elif mode == "OTM_1":
        return (atm + step) if side == "CE" else (atm - step)
    return atm

def show_real_trade_report(connector=None):
    print("\n" + "=" * 82)
    print("   ALGO REAL TRADE REPORT (KITNE REAL TRADE LIYE GAYE HAIN)")
    print("=" * 82)
    csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
    if os.path.exists(csv_file):
        df_local = pd.read_csv(csv_file)
        if not df_local.empty:
            total_real = len(df_local)
            executed_orders = len(df_local[df_local["OrderPlaced"] == True]) if "OrderPlaced" in df_local.columns else total_real
            closed_df = df_local[df_local["Status"] == "CLOSED"] if "Status" in df_local.columns else df_local
            open_df = df_local[df_local["Status"] == "OPEN"] if "Status" in df_local.columns else pd.DataFrame()
            wins = len(closed_df[closed_df["PnL_Pts"] > 0]) if "PnL_Pts" in closed_df.columns else 0
            losses = len(closed_df[closed_df["PnL_Pts"] <= 0]) if "PnL_Pts" in closed_df.columns else 0
            net_pts = closed_df["PnL_Pts"].sum() if "PnL_Pts" in closed_df.columns else 0.0
            print(f"[A] ALGO JOURNAL RECORD ({csv_file}):")
            print(f"    Total Blue Arrow Real Trades : {total_real} (Broker Live Orders Sent: {executed_orders})")
            print(f"    Open Trades: {len(open_df)} | Closed Trades: {len(closed_df)} (Win: {wins} / Loss: {losses}) | Net P&L: {net_pts:+.2f} pts")
            print("-" * 82)
            print(df_local.to_string(index=False))
        else:
            print(f"[A] ALGO JOURNAL RECORD: Abhi tak 0 real trades record hue hain.")
    else:
        print(f"[A] ALGO JOURNAL RECORD: Abhi tak koi real trade file nahi bani hai (0 Real Trades).")

    if connector is not None:
        print("\n" + "-" * 82)
        print(f"[B] BROKER ({connector.broker}) AAJ KI LIVE ORDER & POSITION BOOK:")
        try:
            broker_summary = connector.get_broker_live_trade_summary()
            print(broker_summary)
        except Exception as e:
            print(f"    Broker book fetch info: {e}")
    print("=" * 82 + "\n")
    show_paper_trade_report(connector)


def interactive_option_selector(connector=None):
    if not CONFIG.get("INTERACTIVE_MENU", True) or os.environ.get("GITHUB_ACTIONS") == "true":
        return
    print("\n" + "=" * 68)
    print("   NIFTY OPTION SIGNAL PRO v28 - OPTION & BACKTEST SELECTOR")
    print("=" * 68)
    m_in = input("\n[1] Mode Chunein (1=LIVE, 2=BACKTEST, 3=REAL TRADE REPORT, Enter=1): ").strip()
    if m_in == "3":
        show_real_trade_report(connector)
        cont = input("Kya ab LIVE ya BACKTEST chalana hai? (1=LIVE, 2=BACKTEST, Enter=Exit): ").strip()
        if cont not in ("1", "2"):
            raise SystemExit(0)
        m_in = cont
    if m_in == "2":
        CONFIG["RUN_MODE"] = "BACKTEST"
        d_in = input(f"    Kitne din ka Backtest chahiye? (Enter={CONFIG['BACKTEST_DAYS']}): ").strip()
        if d_in.isdigit() and int(d_in) > 0:
            CONFIG["BACKTEST_DAYS"] = int(d_in)
        bt_in = input("    Backtest Type (1=BOTH, 2=REAL_BLUE_ONLY, 3=ALL_SIGNALS, Enter=1): ").strip()
        bt_map = {"1": "BOTH", "2": "REAL_BLUE_ONLY", "3": "ALL_SIGNALS"}
        if bt_in in bt_map:
            CONFIG["BACKTEST_ENTRY_TYPE"] = bt_map[bt_in]
    else:
        CONFIG["RUN_MODE"] = "LIVE"

    s_in = input("\n[2] Strike Selection (1=ATM, 2=ITM_1, 3=ITM_2, 4=OTM_1, Enter=1): ").strip()
    strike_map = {"1": "ATM", "2": "ITM_1", "3": "ITM_2", "4": "OTM_1"}
    if s_in in strike_map:
        PARAMS["strikeMode"] = strike_map[s_in]

    e_in = input("\n[3] Expiry Selection (1=CURRENT_WEEK, 2=NEXT_WEEK, 3=MONTHLY, 4=MANUAL, Enter=1): ").strip()
    exp_map = {"1": "CURRENT_WEEK", "2": "NEXT_WEEK", "3": "MONTHLY", "4": "MANUAL"}
    if e_in in exp_map:
        PARAMS["expiryMode"] = exp_map[e_in]
        if PARAMS["expiryMode"] == "MANUAL":
            dt_in = input("    Expiry Date likhein (e.g. 2026-11-24): ").strip()
            if dt_in:
                PARAMS["manualExpiry"] = dt_in

    x_in = input("\n[4] Target Exit Option (1=T1, 2=T2, 3=T1_T2, 4=MANUAL, Enter=1): ").strip()
    exit_map = {"1": "T1", "2": "T2", "3": "T1_T2", "4": "MANUAL"}
    if x_in in exit_map:
        PARAMS["exitMode"] = exit_map[x_in]

    oi_in = input(f"\n[5] Option OI Strike Span [2-9] (Enter={PARAMS['ocN']}): ").strip()
    if oi_in.isdigit() and 2 <= int(oi_in) <= 9:
        PARAMS["ocN"] = int(oi_in)
    vol_in = input(f"    Option Volume PCR Strike Span [2-9] (Enter={PARAMS['ovN']}): ").strip()
    if vol_in.isdigit() and 2 <= int(vol_in) <= 9:
        PARAMS["ovN"] = int(vol_in)

    if CONFIG["RUN_MODE"] == "LIVE":
        o_in = input("\n[6] Order Execution (1=Safe Alert Mode, 2=AUTO LIVE ORDER, Enter=1): ").strip()
        CONFIG["AUTO_PLACE_ORDER"] = (o_in == "2")
        p_in = input("    Paper Trading (virtual orders, real option LTP par)? (1=OFF, 2=ON, Enter=1): ").strip()
        CONFIG["PAPER_TRADING"] = (p_in == "2")
        if CONFIG["PAPER_TRADING"]:
            CONFIG["AUTO_PLACE_ORDER"] = False  # paper ON ho to real order kabhi nahi jayega
            pc_in = input(f"    Paper Capital Rs (Enter={CONFIG['PAPER_CAPITAL']:.0f}): ").strip()
            if pc_in.replace(".", "", 1).isdigit() and float(pc_in) > 0:
                CONFIG["PAPER_CAPITAL"] = float(pc_in)

    d_in2 = input("\n[7] Dashboard (1=ON, 2=OFF, 3=ON+Console, Enter=1): ").strip()
    CONFIG["DASH_ON"] = (d_in2 != "2")
    CONFIG["DASH_CONSOLE_TABLES"] = (d_in2 == "3")


BREADTH_STOCKS = [
    ("HDFCBANK", 9.85), ("ICICIBANK", 9.45), ("RELIANCE", 7.83), ("BHARTIARTL", 5.00),
    ("LT", 4.30), ("INFY", 4.00), ("SBIN", 3.70), ("AXISBANK", 3.22),
    ("ITC", 3.20), ("TCS", 2.80), ("KOTAKBANK", 2.80), ("M&M", 2.80),
    ("BAJFINANCE", 2.63), ("HINDUNILVR", 2.10), ("MARUTI", 1.90), ("ETERNAL", 1.90),
    ("SUNPHARMA", 1.80), ("NTPC", 1.60), ("TITAN", 1.60), ("HCLTECH", 1.40)
]

SECTOR_MAP = {
    "Financial Svc": {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK", "BAJFINANCE", "BAJAJFINSV", "SHRIRAMFIN", "HDFCLIFE", "SBILIFE", "JIOFIN"},
    "Oil & Gas": {"RELIANCE", "ONGC", "BPCL", "COALINDIA"},
    "IT": {"INFY", "TCS", "HCLTECH", "WIPRO", "TECHM", "LTIM"},
    "Auto": {"M&M", "M_M", "MARUTI", "TATAMOTORS", "TMPV", "BAJAJ-AUTO", "BAJAJ_AUTO", "EICHERMOT", "HEROMOTOCO"},
    "Telecom": {"BHARTIARTL"},
    "FMCG": {"ITC", "HINDUNILVR", "NESTLEIND", "TATACONSUM", "BRITANNIA"},
    "Healthcare": {"SUNPHARMA", "CIPLA", "DRREDDY", "APOLLOHOSP"},
    "Metals": {"TATASTEEL", "JSWSTEEL", "HINDALCO", "ADANIENT"},
    "Construction": {"LT"},
    "Cons Services": {"ETERNAL", "TRENT"},
    "Cons Durables": {"TITAN", "ASIANPAINT"},
    "Power": {"NTPC", "POWERGRID"},
    "Services": {"ADANIPORTS", "INDIGO"},
    "Constr Material": {"ULTRACEMCO", "GRASIM"},
    "Capital Goods": {"BEL", "SIEMENS"},
}
BANK_STOCKS = {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK"}
DOW_MAP = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
IST = pytz.timezone("Asia/Kolkata")


# ==============================================================================
# 3. EXACT PINE SCRIPT TECHNICAL MATH
# ==============================================================================
def parse_hhmm(t_str: str) -> dt.time:
    h, m = map(int, t_str.split(":"))
    return dt.time(h, m)

def in_session(ts: dt.datetime, start_str: str, end_str: str) -> bool:
    t = ts.time()
    return parse_hhmm(start_str) <= t <= parse_hhmm(end_str)

def calc_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def calc_sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length).mean()

def calc_rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1.0 / length, adjust=False).mean()

def calc_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = calc_rma(gain, length)
    avg_loss = calc_rma(loss, length)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def calc_atr(df: pd.DataFrame, length: int = 10) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return calc_rma(tr, length)

def calc_dmi(df: pd.DataFrame, length: int = 14):
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_s = calc_rma(tr, length)

    di_plus = 100.0 * calc_rma(plus_dm, length) / atr_s.replace(0, np.nan)
    di_minus = 100.0 * calc_rma(minus_dm, length) / atr_s.replace(0, np.nan)
    dx = 100.0 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = calc_rma(dx, length)
    return di_plus, di_minus, adx

def calc_supertrend(df: pd.DataFrame, factor: float = 3.0, atr_period: int = 10) -> pd.Series:
    atr = calc_atr(df, atr_period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upperband = (hl2 + factor * atr).values
    lowerband = (hl2 - factor * atr).values
    close = df["close"].values
    n = len(df)

    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    sdir = np.ones(n)

    for i in range(n):
        if i == 0:
            final_ub[i] = upperband[i]
            final_lb[i] = lowerband[i]
            sdir[i] = 1
            continue
        final_ub[i] = upperband[i] if (upperband[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]) else final_ub[i-1]
        final_lb[i] = lowerband[i] if (lowerband[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]) else final_lb[i-1]

        if sdir[i-1] == 1 and close[i] > final_ub[i-1]:
            sdir[i] = -1
        elif sdir[i-1] == -1 and close[i] < final_lb[i-1]:
            sdir[i] = 1
        else:
            sdir[i] = sdir[i-1]

    return pd.Series(sdir, index=df.index)

def calc_vwap(df: pd.DataFrame) -> pd.Series:
    if "volume" not in df.columns or df["volume"].fillna(0).sum() <= 0:
        return pd.Series(np.nan, index=df.index)
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0
    dates = df.index.date
    pv = hlc3 * df["volume"]
    cum_pv = pv.groupby(dates).cumsum()
    cum_vol = df["volume"].groupby(dates).cumsum()
    return cum_pv / cum_vol.replace(0, np.nan)


# ==============================================================================
# 4A. PAPER TRADING ENGINE (LIVE MARKET ME VIRTUAL ORDERS - REAL OPTION LTP PAR FILL)
# ==============================================================================
def _pnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def _paper_append_csv(path, row):
    try:
        pd.DataFrame([row]).to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    except Exception as e:
        print(f"[Paper CSV Error] {e}")


class PaperTrader:
    """Virtual ledger: BUY/SELL orders ko real option chain LTP par fill karta hai.
    Brokerage + slippage lagta hai, CSV + JSON me save hota hai (restart safe)."""

    def __init__(self):
        self.orders_csv = CONFIG.get("PAPER_ORDERS_CSV", "paper_orders_log.csv")
        self.trades_csv = CONFIG.get("PAPER_TRADES_CSV", "paper_trades_journal.csv")
        self.state_json = CONFIG.get("PAPER_STATE_JSON", "paper_open_positions.json")
        self.open = {}
        self.trade_seq = 0
        self._load()

    @staticmethod
    def _key(side, strike, expiry):
        return f"{side}|{int(strike)}|{expiry}"

    def _load(self):
        if os.path.exists(self.state_json):
            try:
                with open(self.state_json, "r", encoding="utf-8") as f:
                    st_ = json.load(f)
                self.open = st_.get("open", {}) or {}
                self.trade_seq = int(st_.get("trade_seq", 0))
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_json, "w", encoding="utf-8") as f:
                json.dump({"open": self.open, "trade_seq": self.trade_seq}, f)
        except Exception as e:
            print(f"[Paper State Error] {e}")

    def reset(self):
        for p in (self.orders_csv, self.trades_csv, self.state_json):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self.open = {}
        self.trade_seq = 0

    def _log_order(self, now, action, side, strike, expiry, qty, fill, spot, fee, src, status, note=""):
        _paper_append_csv(self.orders_csv, {
            "Time": now.strftime("%Y-%m-%d %H:%M:%S"), "Action": action,
            "Contract": f"NIFTY {int(strike)} {side}", "Expiry": expiry,
            "Lots": int(round(qty / PARAMS["optLot"])) if PARAMS["optLot"] else 0, "Qty": int(qty),
            "FillPremium": (round(fill, 2) if not _pnan(fill) else None),
            "Spot": (round(float(spot), 2) if not _pnan(spot) else None),
            "Fee_Rs": round(fee, 2), "PriceSource": src, "Status": status, "Note": note})

    def buy(self, side, strike, expiry, lots, prem, spot, src="CHAIN_LTP"):
        qty = int(lots * PARAMS["optLot"])
        slip = float(CONFIG.get("PAPER_SLIPPAGE_PTS", 0.0))
        fee = float(CONFIG.get("PAPER_BROKERAGE_PER_ORDER", 20.0))
        fill = (float(prem) + slip) if not _pnan(prem) else float("nan")
        now = dt.datetime.now(IST)
        key = self._key(side, strike, expiry)
        pos = self.open.get(key)
        if pos is None:
            self.trade_seq += 1
            pos = dict(id=f"PT-{now:%Y%m%d}-{self.trade_seq}", side=side, strike=float(strike), expiry=expiry,
                       qty=0, lots=0, avg=float("nan"), entry_time=now.strftime("%Y-%m-%d %H:%M:%S"),
                       entry_spot=(float(spot) if not _pnan(spot) else float("nan")), fees=0.0,
                       src=src, mode=PARAMS["strikeMode"])
            self.open[key] = pos
        if pos["qty"] > 0 and not _pnan(pos["avg"]) and not _pnan(fill):
            pos["avg"] = (pos["avg"] * pos["qty"] + fill * qty) / (pos["qty"] + qty)
        elif pos["qty"] == 0:
            pos["avg"] = fill
        pos["qty"] += qty
        pos["lots"] += int(lots)
        pos["fees"] += fee
        if _pnan(fill):
            pos["src"] = "SPOT_DELTA_EST"
        self._log_order(now, "BUY", side, strike, expiry, qty, fill, spot, fee, ("CHAIN_LTP" if not _pnan(fill) else "SPOT_DELTA_EST"), "FILLED")
        self._save()
        return dict(id=pos["id"], qty=qty, fill=fill, fee=fee)

    def sell(self, side, strike, expiry, lots, prem, spot, reason="SELL"):
        key = self._key(side, strike, expiry)
        pos = self.open.get(key)
        now = dt.datetime.now(IST)
        fee = float(CONFIG.get("PAPER_BROKERAGE_PER_ORDER", 20.0))
        slip = float(CONFIG.get("PAPER_SLIPPAGE_PTS", 0.0))
        fill = (float(prem) - slip) if not _pnan(prem) else float("nan")
        want_qty = int(lots * PARAMS["optLot"])
        if pos is None or pos["qty"] <= 0:
            self._log_order(now, "SELL", side, strike, expiry, want_qty, fill, spot, 0.0, "-", "IGNORED",
                            "Paper me is contract ki koi open BUY position nahi thi (Blue Arrow se pehle exit)")
            return None
        qty = min(want_qty, int(pos["qty"]))
        if qty <= 0:
            return None
        before = pos["qty"]
        entry_fee_share = pos["fees"] * (qty / before)
        pos["fees"] -= entry_fee_share
        if not _pnan(fill) and not _pnan(pos["avg"]):
            prem_pts = fill - pos["avg"]
            src = "CHAIN_LTP"
        else:
            sgn = 1 if side == "CE" else -1
            if _pnan(spot) or _pnan(pos["entry_spot"]):
                prem_pts, src = 0.0, "NO_PRICE"
            else:
                prem_pts = sgn * (float(spot) - pos["entry_spot"]) * PARAMS["optDelta"]
                src = "SPOT_DELTA_EST"
        gross = prem_pts * qty
        fees = entry_fee_share + fee
        net = gross - fees
        pos["qty"] -= qty
        pos["lots"] = max(0, pos["lots"] - int(round(qty / PARAMS["optLot"])))
        closed = pos["qty"] <= 0
        row = {
            "TradeID": pos["id"], "Date": now.strftime("%Y-%m-%d"),
            "EntryTime": pos["entry_time"], "ExitTime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "Contract": f"NIFTY {int(strike)} {side}", "StrikeMode": pos.get("mode", PARAMS["strikeMode"]), "Expiry": expiry,
            "Lots": int(round(qty / PARAMS["optLot"])), "Qty": qty,
            "EntrySpot": (round(pos["entry_spot"], 2) if not _pnan(pos["entry_spot"]) else None),
            "ExitSpot": (round(float(spot), 2) if not _pnan(spot) else None),
            "EntryPremium": (round(pos["avg"], 2) if not _pnan(pos["avg"]) else None),
            "ExitPremium": (round(fill, 2) if not _pnan(fill) else None),
            "PnL_Prem_Pts": round(prem_pts, 2), "GrossPnL_Rs": round(gross, 2),
            "Fees_Rs": round(fees, 2), "NetPnL_Rs": round(net, 2),
            "ExitReason": reason, "PriceSource": src, "Status": ("CLOSED" if closed else "PARTIAL")}
        _paper_append_csv(self.trades_csv, row)
        self._log_order(now, "SELL", side, strike, expiry, qty, fill, spot, fee, src, "FILLED", reason)
        if closed:
            del self.open[key]
        self._save()
        return row

    def trades_df(self):
        if os.path.exists(self.trades_csv):
            try:
                return pd.read_csv(self.trades_csv)
            except Exception:
                pass
        return pd.DataFrame()

    def orders_df(self):
        if os.path.exists(self.orders_csv):
            try:
                return pd.read_csv(self.orders_csv)
            except Exception:
                pass
        return pd.DataFrame()

    def summary(self, connector=None):
        df = self.trades_df()
        d = dict(legs=0, wins=0, losses=0, gross=0.0, fees=0.0, net=0.0, win_rate=float("nan"), unreal=0.0, open=[])
        if not df.empty and "NetPnL_Rs" in df.columns:
            d["legs"] = len(df)
            d["wins"] = int((df["NetPnL_Rs"] > 0).sum())
            d["losses"] = int((df["NetPnL_Rs"] <= 0).sum())
            d["gross"] = float(df["GrossPnL_Rs"].sum())
            d["fees"] = float(df["Fees_Rs"].sum())
            d["net"] = float(df["NetPnL_Rs"].sum())
            d["win_rate"] = d["wins"] * 100.0 / d["legs"] if d["legs"] > 0 else float("nan")
        for key, pos in self.open.items():
            ltp = connector._paper_ltp(pos["side"], pos["strike"]) if connector is not None else float("nan")
            un = float("nan")
            if not _pnan(ltp) and not _pnan(pos["avg"]):
                un = (ltp - pos["avg"]) * pos["qty"]
                d["unreal"] += un
            d["open"].append({
                "TradeID": pos["id"], "Contract": f"NIFTY {int(pos['strike'])} {pos['side']}", "Expiry": pos["expiry"],
                "Lots": pos["lots"], "Qty": pos["qty"], "EntryTime": pos["entry_time"],
                "AvgEntryPremium": (round(pos["avg"], 2) if not _pnan(pos["avg"]) else None),
                "LTP_Now": (round(ltp, 2) if not _pnan(ltp) else None),
                "Unrealized_Rs": (round(un, 2) if not _pnan(un) else None)})
        d["equity"] = float(CONFIG.get("PAPER_CAPITAL", 100000.0)) + d["net"] + d["unreal"]
        return d


def show_paper_trade_report(connector=None):
    if not (CONFIG.get("PAPER_TRADING", False) or os.path.exists(CONFIG.get("PAPER_TRADES_CSV", "paper_trades_journal.csv"))
            or os.path.exists(CONFIG.get("PAPER_STATE_JSON", "paper_open_positions.json"))):
        return
    pt = connector._get_paper() if connector is not None else PaperTrader()
    s = pt.summary(connector)
    print("\n" + "=" * 82)
    print("   PAPER TRADING REPORT (VIRTUAL - REAL OPTION LTP PAR FILL)")
    print("=" * 82)
    print(f"    Paper Capital: Rs {CONFIG.get('PAPER_CAPITAL', 100000.0):,.0f} | Equity: Rs {s['equity']:,.0f}")
    print(f"    Exit Legs: {s['legs']} (Win {s['wins']} / Loss {s['losses']}) | Gross: Rs {s['gross']:+,.0f} | Fees: Rs {s['fees']:,.0f} | Net: Rs {s['net']:+,.0f} | Open Unrealized: Rs {s['unreal']:+,.0f}")
    if s["open"]:
        print("    OPEN POSITIONS:")
        print(pd.DataFrame(s["open"]).to_string(index=False))
    df = pt.trades_df()
    if not df.empty:
        print("-" * 82)
        print(df.to_string(index=False))
    print("=" * 82 + "\n")


def paper_panel_streamlit(connector=None, key_prefix="pp"):
    import streamlit as st
    pt = connector._get_paper() if connector is not None else PaperTrader()
    s = pt.summary(connector)
    st.subheader("PAPER TRADING (Virtual Orders - Real Option LTP Fill)")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Paper Equity (Rs)", f"{s['equity']:,.0f}", f"{s['net'] + s['unreal']:+,.0f}")
    m2.metric("Realized Net P&L (Rs)", f"{s['net']:+,.0f}")
    m3.metric("Open Unrealized (Rs)", f"{s['unreal']:+,.0f}", f"{len(s['open'])} open")
    m4.metric("Exit Legs  W / L", f"{s['wins']} / {s['losses']}")
    m5.metric("Win Rate", "--" if _pnan(s["win_rate"]) else f"{s['win_rate']:.0f}%")
    st.caption(f"Capital Rs {CONFIG.get('PAPER_CAPITAL', 100000.0):,.0f} | Brokerage Rs {CONFIG.get('PAPER_BROKERAGE_PER_ORDER', 20.0):.0f}/order | "
               f"Slippage {CONFIG.get('PAPER_SLIPPAGE_PTS', 0.0):.1f} pts | Fees total Rs {s['fees']:,.0f}")
    if s["open"]:
        st.markdown("**Open Paper Positions**")
        st.dataframe(pd.DataFrame(s["open"]), use_container_width=True)
    else:
        st.info("Abhi koi open paper position nahi hai. Blue Arrow (Final Buy) par virtual BUY apne aap lagega.")
    df_t = pt.trades_df()
    if not df_t.empty:
        st.markdown("**Paper Trades Journal**")
        st.dataframe(df_t, use_container_width=True)
        st.download_button("Download Paper Trades CSV", df_t.to_csv(index=False).encode("utf-8"),
                           CONFIG.get("PAPER_TRADES_CSV", "paper_trades_journal.csv"), "text/csv", key=f"{key_prefix}_dl_trades")
    df_o = pt.orders_df()
    if not df_o.empty:
        with st.expander("Paper Orders Log (har BUY / SELL order)"):
            st.dataframe(df_o, use_container_width=True)
            st.download_button("Download Paper Orders CSV", df_o.to_csv(index=False).encode("utf-8"),
                               CONFIG.get("PAPER_ORDERS_CSV", "paper_orders_log.csv"), "text/csv", key=f"{key_prefix}_dl_orders")
    with st.expander("Reset Paper Ledger"):
        sure = st.checkbox("Haan, saara paper trade record delete karna hai", key=f"{key_prefix}_sure")
        if st.button("Reset Paper Ledger", key=f"{key_prefix}_reset") and sure:
            pt.reset()
            st.success("Paper ledger reset ho gaya. Page refresh karein.")


# ==============================================================================
# 4. BROKER CONNECTOR
# ==============================================================================
# ==============================================================================
# 3B. OPTION PREMIUM (Rs) HELPERS: contract naam, Black-Scholes fallback, backtest price provider
# ==============================================================================
def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_option_price(spot, strike, t_years, iv, side, r=0.07):
    """Black-Scholes European option price (ESTIMATE). iv = 0.15 matlab 15%."""
    try:
        spot, strike, iv = float(spot), float(strike), float(iv)
    except Exception:
        return float("nan")
    if not (spot > 0 and strike > 0) or spot != spot or iv != iv:
        return float("nan")
    intrinsic = max(spot - strike, 0.0) if side == "CE" else max(strike - spot, 0.0)
    if not (iv > 0 and t_years > 0):
        return intrinsic
    sq = iv * math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / sq
    d2 = d1 - sq
    disc = math.exp(-r * t_years)
    if side == "CE":
        return spot * _norm_cdf(d1) - strike * disc * _norm_cdf(d2)
    return strike * disc * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def fmt_contract(side, strike, expiry):
    """Poora contract naam, jaise: NIFTY 24 Nov 2026 25400 CE"""
    try:
        e = pd.Timestamp(str(expiry)[:10]).strftime("%d %b %Y")
    except Exception:
        e = str(expiry)
    return f"NIFTY {e} {int(strike)} {side}"


class OptionPriceProvider:
    """Backtest ke liye option premium (Rs).
    Priority: (1) broker ke real 1-min option candles (abhi chal rahi expiry ke contracts)
              (2) Dhan Rolling Option API (expire ho chuke contracts, best-effort)
              (3) Black-Scholes + India VIX ESTIMATE  (PriceSource = EST_BS)
    """
    def __init__(self, broker):
        self.b = broker
        self.cache = {}
        self.warned = set()

    def _warn(self, key, msg):
        if key not in self.warned:
            self.warned.add(key)
            print(msg)

    def _series(self, side, strike, exp_date, day):
        key = (side, int(strike), str(exp_date), str(day))
        if key in self.cache:
            return self.cache[key]
        s, src = None, ""
        try:
            df = self.b.get_option_candles_1m(side, strike, exp_date, day)
            if df is not None and not df.empty:
                s, src = df["close"].astype(float), f"{self.b.broker}_REAL"
        except Exception as e:
            self._warn("real", f"[Option Price] real option candles error: {e}")
        if s is None and CONFIG.get("BT_USE_ROLLING_API", True) and self.b.broker == "DHAN":
            try:
                df = self.b.get_rolling_option_1m(side, strike, day)
                if df is not None and not df.empty:
                    s, src = df["close"].astype(float), "DHAN_ROLLING"
            except Exception as e:
                self._warn("roll", f"[Option Price] rolling option API error: {e}")
        self.cache[key] = (s, src)
        return s, src

    def price_at(self, side, strike, exp_date, ts, spot, vix_val):
        """ts = 5m bar ka start time; premium = us bar ke aakhri minute ka close. Returns (price, source)."""
        ts = pd.Timestamp(ts)
        tgt = ts + pd.Timedelta(minutes=4)
        s, src = self._series(side, strike, exp_date, ts.date())
        if s is not None and not s.empty:
            sub = s[s.index <= tgt]
            if not sub.empty and (tgt - sub.index[-1]) <= pd.Timedelta(minutes=15):
                v = float(sub.iloc[-1])
                if v > 0:
                    return round(v, 2), src
        try:
            iv = float(vix_val) / 100.0
            e_naive = dt.datetime.combine(pd.Timestamp(str(exp_date)[:10]).date(), dt.time(15, 30))
            exp_dt = IST.localize(e_naive)
            now_end = (ts + pd.Timedelta(minutes=5)).to_pydatetime()
            t_years = max((exp_dt - now_end).total_seconds(), 60.0) / (365.0 * 86400.0)
            p = bs_option_price(spot, strike, t_years, iv, side, CONFIG.get("BT_RISK_FREE", 0.07))
            if p == p:
                return round(p, 2), "EST_BS"
        except Exception as e:
            self._warn("bs", f"[Option Price] Black-Scholes fallback error: {e}")
        return float("nan"), "NA"


class BrokerConnector:
    def __init__(self, cfg):
        self.broker = cfg["BROKER"].upper()
        self.cfg = cfg
        self.dhan = None
        if self.broker == "DHAN":
            import dhanhq as _dh
            token = str(cfg["DHAN_ACCESS_TOKEN"]).strip()
            cid = str(cfg["DHAN_CLIENT_ID"]).strip()
            dhanhq = _dh.dhanhq
            last_err = None
            try:
                DhanContext = getattr(_dh, "DhanContext", None)
                if DhanContext is None:
                    from dhanhq.dhan_context import DhanContext
                self.dhan = dhanhq(DhanContext(cid, token))
            except Exception as e1:
                last_err = e1
                try:
                    self.dhan = dhanhq(cid, token)
                except Exception as e2:
                    last_err = e2
                    try:
                        self.dhan = dhanhq(client_id=cid, access_token=token)
                    except Exception as e3:
                        raise RuntimeError(f"Dhan init failed: {last_err} | {e3}")
        elif self.broker == "UPSTOX":
            self.headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {str(cfg['UPSTOX_ACCESS_TOKEN']).strip()}"
            }
        else:
            raise ValueError("BROKER sirf 'DHAN' ya 'UPSTOX' hona chahiye.")
        self.inst = self._load_master()

    def _load_master(self) -> dict:
        m = {}
        if self.broker == "DHAN":
            df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
            idx = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_TRADING_SYMBOL"] == "NIFTY")]
            if "SEM_INSTRUMENT_NAME" in idx.columns:
                _idx_only = idx[idx["SEM_INSTRUMENT_NAME"] == "INDEX"]
                if not _idx_only.empty:
                    idx = _idx_only
            if not idx.empty:
                m["NIFTY_SPOT"] = str(idx.iloc[0]["SEM_SMST_SECURITY_ID"])
            vix = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_TRADING_SYMBOL"] == "INDIA VIX")]
            if not vix.empty:
                m["INDIAVIX"] = str(vix.iloc[0]["SEM_SMST_SECURITY_ID"])
            fut = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "FUTIDX") & (df["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-"))].sort_values("SEM_EXPIRY_DATE")
            if not fut.empty:
                m["NIFTY_FUT"] = str(fut.iloc[0]["SEM_SMST_SECURITY_ID"])
            eq = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")]
            for sym, _ in BREADTH_STOCKS:
                row = eq[eq["SEM_TRADING_SYMBOL"] == sym]
                if not row.empty:
                    m[sym] = str(row.iloc[0]["SEM_SMST_SECURITY_ID"])
            m["_DF"] = df

        elif self.broker == "UPSTOX":
            df = pd.read_json("https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz", compression="gzip")
            m["NIFTY_SPOT"] = "NSE_INDEX|Nifty 50"
            m["INDIAVIX"] = "NSE_INDEX|India VIX"
            fut = df[(df["segment"] == "NSE_FO") & (df["instrument_type"] == "FUT") & (df["name"] == "NIFTY")].sort_values("expiry")
            if not fut.empty:
                m["NIFTY_FUT"] = fut.iloc[0]["instrument_key"]
            eq = df[df["segment"] == "NSE_EQ"]
            for sym, _ in BREADTH_STOCKS:
                row = eq[eq["trading_symbol"] == sym]
                if not row.empty:
                    m[sym] = row.iloc[0]["instrument_key"]
            m["_DF"] = df
        return m

    # ---------------- OPTION PREMIUM / EXPIRY HELPERS ----------------
    last_order_info = {}

    def _all_master_expiries(self) -> list:
        """Scrip master me jitni Nifty option expiries listed hain (aaj se pehle ki nahi hoti)."""
        if getattr(self, "_exp_all_cache", None) is not None:
            return self._exp_all_cache
        exps = []
        try:
            df_m = self.inst["_DF"]
            if self.broker == "DHAN":
                opt_df = df_m[(df_m["SEM_EXM_EXCH_ID"] == "NSE") & (df_m["SEM_INSTRUMENT_NAME"] == "OPTIDX") & (df_m["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-"))]
                exps = sorted({str(e)[:10] for e in opt_df["SEM_EXPIRY_DATE"].unique()})
            else:
                opt_df = df_m[(df_m["segment"] == "NSE_FO") & (df_m["instrument_type"].isin(["CE", "PE"])) & (df_m["name"] == "NIFTY")]
                exps = sorted({dt.datetime.fromtimestamp(e / 1000, IST).strftime("%Y-%m-%d") for e in opt_df["expiry"].unique()})
        except Exception:
            exps = []
        self._exp_all_cache = exps
        return exps

    def _expiry_weekday(self) -> int:
        """Weekly expiry kis din hoti hai (master se nikalta hai; na mile to Tuesday)."""
        exps = self._all_master_expiries()[:8]
        if exps:
            wds = [pd.Timestamp(e).weekday() for e in exps]
            return max(set(wds), key=wds.count)
        return 1

    def resolve_expiry_date(self, on_date):
        """Kisi bhi trade-date ke liye asli expiry date (YYYY-MM-DD) + source ('MASTER' / 'RULE_EST' / 'MANUAL').
        RULE_EST = contract expire ho chuka hai, weekday rule se nikali date (holiday shift ho to galat ho sakti hai)."""
        mode = PARAMS["expiryMode"].upper()
        if mode == "MANUAL" and PARAMS["manualExpiry"].strip():
            return PARAMS["manualExpiry"].strip(), "MANUAL"
        d = pd.Timestamp(on_date).date()
        ds = d.strftime("%Y-%m-%d")
        exps = self._all_master_expiries()
        wd = self._expiry_weekday()
        rule = d + dt.timedelta(days=(wd - d.weekday()) % 7)
        if mode == "NEXT_WEEK":
            rule += dt.timedelta(days=7)
        elif mode == "MONTHLY":
            def _last_wd(y, m):
                nxt = dt.date(y + (1 if m == 12 else 0), (m % 12) + 1, 1)
                last = nxt - dt.timedelta(days=1)
                return last - dt.timedelta(days=(last.weekday() - wd) % 7)
            rule = _last_wd(d.year, d.month)
            if rule < d:
                rule = _last_wd(d.year + (1 if d.month == 12 else 0), (d.month % 12) + 1)
        rule_s = rule.strftime("%Y-%m-%d")
        if exps and rule_s in exps:
            return rule_s, "MASTER"
        if exps and rule_s >= exps[0]:
            cand = [e for e in exps if e >= ds]
            if cand:
                if mode == "NEXT_WEEK" and len(cand) > 1:
                    return cand[1], "MASTER"
                if mode == "MONTHLY":
                    me = [e for e in cand if e.startswith(cand[0][:7])]
                    return (me[-1] if me else cand[0]), "MASTER"
                return cand[0], "MASTER"
        return rule_s, "RULE_EST"

    def _option_sec_id(self, side: str, strike: float, exp: str):
        df_m = self.inst["_DF"]
        exp = str(exp)[:10]
        if self.broker == "DHAN":
            o = df_m[(df_m["SEM_EXM_EXCH_ID"] == "NSE") & (df_m["SEM_INSTRUMENT_NAME"] == "OPTIDX") &
                     (df_m["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-")) & (df_m["SEM_OPTION_TYPE"] == side) &
                     (df_m["SEM_STRIKE_PRICE"] == float(strike)) &
                     (df_m["SEM_EXPIRY_DATE"].astype(str).str.startswith(exp))]
            return str(o.iloc[0]["SEM_SMST_SECURITY_ID"]) if not o.empty else None
        o = df_m[(df_m["segment"] == "NSE_FO") & (df_m["name"] == "NIFTY") & (df_m["instrument_type"] == side) &
                 (df_m["strike_price"] == float(strike))].copy()
        if o.empty:
            return None
        o["exp_str"] = o["expiry"].apply(lambda x: dt.datetime.fromtimestamp(x / 1000, IST).strftime("%Y-%m-%d"))
        o = o[o["exp_str"] == exp]
        return o.iloc[0]["instrument_key"] if not o.empty else None

    def get_option_candles_1m(self, side: str, strike: float, exp: str, day) -> pd.DataFrame:
        """Ek contract ke us din ke 1-min candles (real broker data). Contract expire ho chuka ho to empty."""
        sec = self._option_sec_id(side, strike, exp)
        if not sec:
            return pd.DataFrame()
        d0 = pd.Timestamp(day).strftime("%Y-%m-%d")
        if self.broker == "DHAN":
            res = self.dhan.intraday_minute_data(
                security_id=sec, exchange_segment="NSE_FNO", instrument_type="OPTIDX",
                from_date=f"{d0} 09:15:00", to_date=f"{d0} 15:30:00", interval=1
            )
            time.sleep(0.25)
            self._note_error(f"OPT {int(strike)} {side}", "1", res)
            d = res.get("data", {}) if isinstance(res, dict) else {}
            if not isinstance(d, dict) or "timestamp" not in d or len(d["timestamp"]) == 0:
                return pd.DataFrame()
            ts_raw = pd.Series(d["timestamp"], dtype="float64")
            if ts_raw.max() < time.time() - 3 * 365 * 86400:
                ts_raw = ts_raw + 315532800
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(ts_raw.values, unit="s", utc=True).tz_convert(IST),
                "open": d["open"], "high": d["high"], "low": d["low"], "close": d["close"]
            }).set_index("timestamp")
            return df[~df.index.duplicated(keep="last")].sort_index()
        # UPSTOX
        r1 = requests.get(f"https://api.upstox.com/v3/historical-candle/{sec}/minutes/1/{d0}/{d0}", headers=self.headers, timeout=10).json()
        rows = (r1.get("data", {}) or {}).get("candles", []) or []
        if d0 == dt.datetime.now(IST).strftime("%Y-%m-%d"):
            r2 = requests.get(f"https://api.upstox.com/v3/historical-candle/intraday/{sec}/minutes/1", headers=self.headers, timeout=10).json()
            rows = ((r2.get("data", {}) or {}).get("candles", []) or []) + rows
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(IST)
        return df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").set_index("timestamp")[["open", "high", "low", "close"]]

    def get_rolling_option_1m(self, side: str, strike: float, day) -> pd.DataFrame:
        """Dhan Expired/Rolling Option API (best-effort, sirf DHAN). ATM-N..ATM+N strikes mangwa kar
        har minute wahi candle leta hai jiska strike locked strike ke barabar ho."""
        if self.broker != "DHAN":
            return pd.DataFrame()
        spot_id = self.inst.get("NIFTY_SPOT")
        if not spot_id:
            return pd.DataFrame()
        d0 = pd.Timestamp(day).normalize()
        d1 = d0 + pd.Timedelta(days=1)
        mode = PARAMS["expiryMode"].upper()
        flag = "MONTH" if mode == "MONTHLY" else "WEEK"
        code = 2 if mode == "NEXT_WEEK" else 1
        headers = {"access-token": str(self.cfg["DHAN_ACCESS_TOKEN"]).strip(),
                   "client-id": str(self.cfg["DHAN_CLIENT_ID"]).strip(),
                   "Content-Type": "application/json", "Accept": "application/json"}
        n = int(CONFIG.get("BT_ROLLING_OFFSETS", 4))
        frames = []
        for k in range(-n, n + 1):
            label = "ATM" if k == 0 else (f"ATM+{k}" if k > 0 else f"ATM{k}")
            payload = {
                "exchangeSegment": "NSE_FNO", "interval": "1", "securityId": int(spot_id), "instrument": "OPTIDX",
                "expiryFlag": flag, "expiryCode": code, "strike": label,
                "drvOptionType": "CALL" if side == "CE" else "PUT",
                "requiredData": ["open", "high", "low", "close", "strike", "spot"],
                "fromDate": d0.strftime("%Y-%m-%d"), "toDate": d1.strftime("%Y-%m-%d"),
            }
            r = requests.post("https://api.dhan.co/v2/charts/rollingoption", json=payload, headers=headers, timeout=20).json()
            time.sleep(0.3)
            data = (r.get("data") or {}) if isinstance(r, dict) else {}
            leg = data.get("ce" if side == "CE" else "pe")
            if not isinstance(leg, dict) or not leg.get("timestamp") or not leg.get("close") or not leg.get("strike"):
                continue
            ts_raw = pd.Series(leg["timestamp"], dtype="float64")
            if ts_raw.max() < time.time() - 3 * 365 * 86400:
                ts_raw = ts_raw + 315532800
            frames.append(pd.DataFrame({
                "timestamp": pd.to_datetime(ts_raw.values, unit="s", utc=True).tz_convert(IST),
                "close": leg["close"], "strike": leg["strike"]
            }))
        if not frames:
            return pd.DataFrame()
        al = pd.concat(frames)
        al = al[pd.to_numeric(al["strike"], errors="coerce").round(2) == round(float(strike), 2)]
        if al.empty:
            return pd.DataFrame()
        al = al.drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp").set_index("timestamp")
        return al[["close"]]

    def _dhan_fill_info(self, res, side: str, strike: float) -> dict:
        """Order ke baad actual fill price (average traded price). Na mile to option-chain LTP (src=CHAIN_LTP)."""
        info = {"price": None, "src": "NA"}
        try:
            if isinstance(res, dict) and str(res.get("status", "")).lower() == "failure":
                print(f"[Order Warning] Dhan ne order reject/fail bataya: {json.dumps(res, default=str)[:300]}")
                return {"price": None, "src": "ORDER_FAILED"}
            oid = ((res or {}).get("data") or {}).get("orderId") if isinstance(res, dict) else None
            if oid:
                for _ in range(4):
                    time.sleep(1.0)
                    od = self.dhan.get_order_by_id(oid)
                    d = od.get("data") if isinstance(od, dict) else None
                    if isinstance(d, list) and d:
                        d = d[0]
                    if isinstance(d, dict):
                        for k in ("averageTradedPrice", "avgTradedPrice", "averagePrice", "tradedPrice"):
                            try:
                                v = float(d.get(k))
                            except Exception:
                                continue
                            if v > 0:
                                return {"price": v, "src": "BROKER_FILL"}
                        st_txt = str(d.get("orderStatus", "")).upper()
                        if st_txt in ("REJECTED", "CANCELLED", "EXPIRED"):
                            return {"price": None, "src": "ORDER_" + st_txt}
        except Exception as e:
            print(f"[Fill Price Error] {e}")
        ltp = self._paper_ltp(side, strike)
        if ltp == ltp:
            return {"price": ltp, "src": "CHAIN_LTP"}
        return info

    def _upstox_fill_info(self, resp, side: str, strike: float) -> dict:
        try:
            j = resp.json()
            if str(j.get("status", "")).lower() == "error":
                print(f"[Order Warning] Upstox order error: {json.dumps(j, default=str)[:300]}")
                return {"price": None, "src": "ORDER_FAILED"}
            ids = (j.get("data") or {}).get("order_ids") or []
            if ids:
                for _ in range(4):
                    time.sleep(1.0)
                    rd = requests.get("https://api.upstox.com/v2/order/details", params={"order_id": ids[0]}, headers=self.headers, timeout=10).json()
                    d = rd.get("data") or {}
                    try:
                        v = float(d.get("average_price"))
                    except Exception:
                        v = 0.0
                    if v > 0:
                        return {"price": v, "src": "BROKER_FILL"}
                    if str(d.get("status", "")).lower() in ("rejected", "cancelled"):
                        return {"price": None, "src": "ORDER_" + str(d.get("status")).upper()}
        except Exception as e:
            print(f"[Fill Price Error] {e}")
        ltp = self._paper_ltp(side, strike)
        if ltp == ltp:
            return {"price": ltp, "src": "CHAIN_LTP"}
        return {"price": None, "src": "NA"}

    # ---------------- PAPER TRADING HELPERS ----------------
    last_ltp_map = {}
    last_spot = float("nan")
    paper = None
    paper_reason = ""

    def _get_paper(self):
        if self.paper is None:
            self.paper = PaperTrader()
        return self.paper

    def _paper_ltp(self, side: str, strike: float) -> float:
        rec = (self.last_ltp_map or {}).get(round(float(strike), 2))
        if rec:
            try:
                v = float(rec.get("ce" if side == "CE" else "pe", np.nan))
                if not np.isnan(v) and v > 0:
                    return v
            except Exception:
                pass
        return float("nan")

    def _paper_notify(self, text: str):
        print(text)
        tok, cid = CONFIG.get("TELEGRAM_BOT_TOKEN", ""), CONFIG.get("TELEGRAM_CHAT_ID", "")
        if tok and cid:
            try:
                requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": text}, timeout=5)
            except Exception:
                pass

    def paper_order(self, side: str, strike: float, lots: int, action: str = "BUY", expiry_date: str = ""):
        pt = self._get_paper()
        exp = expiry_date or self.get_selected_expiry()
        prem = self._paper_ltp(side, strike)
        if np.isnan(prem):
            # option chain ke ATM +-N me ye strike nahi mila: seedha is strike ke liye chain dobara lo
            try:
                _prev = self.last_ltp_map
                time.sleep(3.1)  # Dhan option-chain rate limit (1 request / 3 sec)
                self.get_option_chain_metrics(float(strike), float(strike), PARAMS["ocN"], PARAMS["ovN"])
                prem = self._paper_ltp(side, strike)
                self.last_ltp_map = _prev
            except Exception:
                pass
        spot = self.last_spot
        if action == "BUY":
            r = pt.buy(side, strike, exp, lots, prem, spot)
            self.last_order_info = {"price": (None if np.isnan(r["fill"]) else float(r["fill"])),
                                    "src": ("PAPER_LTP" if not np.isnan(r["fill"]) else "PAPER_EST"), "qty": r["qty"]}
            px_txt = "LTP nahi mila (spot-delta estimate use hoga)" if np.isnan(r["fill"]) else f"{r['fill']:.2f}"
            self._paper_notify(
                f"[PAPER] BUY NIFTY {int(strike)} {side} [{exp}] ({PARAMS['strikeMode']}) | Lots: {lots} (Qty {r['qty']}) "
                f"@ premium {px_txt} | Spot: {spot:.1f} | Trade: {r['id']}"
            )
        else:
            r = pt.sell(side, strike, exp, lots, prem, spot, reason=(self.paper_reason or "SELL"))
            if r is not None:
                try:
                    self.last_order_info = {"price": float(r["ExitPremium"]), "src": str(r.get("PriceSource", "PAPER")), "qty": r.get("Qty")}
                except Exception:
                    pass
            if r is None:
                self._paper_notify(f"[PAPER] SELL ignore hua: NIFTY {int(strike)} {side} ki koi open paper BUY position nahi thi.")
            else:
                self._paper_notify(
                    f"[PAPER] SELL NIFTY {int(strike)} {side} [{exp}] | Qty {r['Qty']} | Entry {r['EntryPremium']} -> Exit {r['ExitPremium']} "
                    f"| {r['ExitReason']} | Net P&L: Rs {r['NetPnL_Rs']:+,.0f} ({r['PriceSource']}) | {r['Status']}"
                )

    def get_broker_live_trade_summary(self) -> str:
        if self.broker == "DHAN":
            orders_res = self.dhan.get_order_list()
            orders = orders_res.get("data", []) if isinstance(orders_res, dict) else []
            pos_res = self.dhan.get_positions()
            positions = pos_res.get("data", []) if isinstance(pos_res, dict) else []
            traded_orders = [o for o in orders if str(o.get("orderStatus", "")).upper() in ("TRADED", "COMPLETE", "FILLED")]
            lines = [f"    Dhan Aaj Ke Total Orders: {len(orders)} | Executed (Traded) Orders: {len(traded_orders)} | Active/Closed Positions: {len(positions)}"]
            for o in traded_orders:
                lines.append(f"      -> {o.get('tradingSymbol')} | {o.get('transactionType')} | Qty: {o.get('quantity')} | Price: {o.get('price')} | Time: {o.get('createTime')}")
            return "\n".join(lines)
        elif self.broker == "UPSTOX":
            r_ord = requests.get("https://api.upstox.com/v2/order/retrieve-all", headers=self.headers, timeout=10).json()
            orders = r_ord.get("data", []) or []
            traded_orders = [o for o in orders if str(o.get("status", "")).lower() == "complete"]
            lines = [f"    Upstox Aaj Ke Total Orders: {len(orders)} | Executed (Complete) Orders: {len(traded_orders)}"]
            for o in traded_orders:
                lines.append(f"      -> {o.get('trading_symbol')} | {o.get('transaction_type')} | Qty: {o.get('quantity')} | AvgPx: {o.get('average_price')} | Time: {o.get('order_timestamp')}")
            return "\n".join(lines)
        return "    Broker order book unavailable."

    def get_all_upcoming_expiries(self) -> list:
        df_m = self.inst["_DF"]
        today_str = dt.datetime.now(IST).strftime("%Y-%m-%d")
        if self.broker == "DHAN":
            opt_df = df_m[(df_m["SEM_EXM_EXCH_ID"] == "NSE") & (df_m["SEM_INSTRUMENT_NAME"] == "OPTIDX") & (df_m["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-"))]
            exps = sorted([str(e)[:10] for e in opt_df["SEM_EXPIRY_DATE"].unique() if str(e)[:10] >= today_str])
        else:
            opt_df = df_m[(df_m["segment"] == "NSE_FO") & (df_m["instrument_type"].isin(["CE", "PE"])) & (df_m["name"] == "NIFTY")]
            exps = sorted(list({dt.datetime.fromtimestamp(e / 1000, IST).strftime("%Y-%m-%d") for e in opt_df["expiry"].unique()}))
            exps = [e for e in exps if e >= today_str]
        return exps

    def get_selected_expiry(self) -> str:
        mode = PARAMS["expiryMode"].upper()
        if mode == "MANUAL" and PARAMS["manualExpiry"].strip():
            return PARAMS["manualExpiry"].strip()

        exps = self.get_all_upcoming_expiries()
        if not exps:
            return ""
        if mode == "NEXT_WEEK" and len(exps) > 1:
            return exps[1]
        if mode == "MONTHLY":
            cur_ym = exps[0][:7]
            month_exps = [e for e in exps if e.startswith(cur_ym)]
            return month_exps[-1] if month_exps else exps[0]
        return exps[0]

    last_error = ""

    def _note_error(self, key, interval, res):
        try:
            if not isinstance(res, dict) or str(res.get("status", "")).lower() != "success":
                msg = f"{key} [{interval}] -> {json.dumps(res, default=str)[:300]}"
                self.last_error = msg
                print(f"[Data Error] {msg}")
        except Exception:
            pass

    def get_candles(self, key: str, interval: str = "5", days: int = 10) -> pd.DataFrame:
        to_dt = dt.datetime.now(IST)
        from_dt = to_dt - dt.timedelta(days=days)

        if self.broker == "DHAN":
            sec_id = self.inst.get(key)
            if not sec_id:
                self.last_error = f"'{key}' ka Security ID scrip master me nahi mila"
                print(f"[Data Error] {self.last_error}")
                return pd.DataFrame()
            seg = "IDX_I" if key in ("NIFTY_SPOT", "INDIAVIX") else ("NSE_FNO" if key == "NIFTY_FUT" else "NSE_EQ")
            itype = "INDEX" if seg == "IDX_I" else ("FUTIDX" if seg == "NSE_FNO" else "EQUITY")

            if interval == "D":
                windows = [(from_dt, to_dt)]
            else:
                windows = []
                w_s = from_dt
                while w_s < to_dt:
                    w_e = min(w_s + dt.timedelta(days=60), to_dt)
                    windows.append((w_s, w_e))
                    w_s = w_e

            frames = []
            for w_from, w_to in windows:
                if interval == "D":
                    res = self.dhan.historical_daily_data(
                        security_id=sec_id, exchange_segment=seg, instrument_type=itype,
                        from_date=w_from.strftime("%Y-%m-%d"), to_date=w_to.strftime("%Y-%m-%d")
                    )
                else:
                    req_int = "1" if interval == "3" else ("60" if interval == "240" else interval)
                    res = self.dhan.intraday_minute_data(
                        security_id=sec_id, exchange_segment=seg, instrument_type=itype,
                        from_date=w_from.strftime("%Y-%m-%d 09:15:00"), to_date=w_to.strftime("%Y-%m-%d 15:30:00"),
                        interval=int(req_int)
                    )
                time.sleep(0.25)  # Dhan data API rate-limit se bachne ke liye
                self._note_error(key, interval, res)
                d = res.get("data", {}) if isinstance(res, dict) else {}
                if not isinstance(d, dict) or "timestamp" not in d or len(d["timestamp"]) == 0:
                    continue
                ts_raw = pd.Series(d["timestamp"], dtype="float64")
                if ts_raw.max() < time.time() - 3 * 365 * 86400:
                    ts_raw = ts_raw + 315532800  # purana Dhan 1980-epoch format fix
                n_rows = len(d["close"])
                fr = pd.DataFrame({
                    "timestamp": pd.to_datetime(ts_raw.values, unit="s", utc=True).tz_convert(IST),
                    "open": d["open"], "high": d["high"], "low": d["low"],
                    "close": d["close"],
                    "volume": d.get("volume", [0] * n_rows),
                    "oi": d.get("open_interest", [0] * n_rows)
                }).set_index("timestamp")
                frames.append(fr)

            if not frames:
                return pd.DataFrame()
            df = pd.concat(frames)
            df = df[~df.index.duplicated(keep="last")].sort_index()

        elif self.broker == "UPSTOX":
            ikey = self.inst.get(key)
            if not ikey:
                self.last_error = f"'{key}' ka instrument key nahi mila"
                return pd.DataFrame()
            umap = {"1": ("minutes", "1"), "3": ("minutes", "1"), "5": ("minutes", "5"),
                    "15": ("minutes", "15"), "60": ("hours", "1"), "240": ("hours", "1"), "D": ("days", "1")}
            utype, uval = umap[interval]
            r1 = requests.get(
                f"https://api.upstox.com/v3/historical-candle/{ikey}/{utype}/{uval}/{to_dt.strftime('%Y-%m-%d')}/{from_dt.strftime('%Y-%m-%d')}",
                headers=self.headers, timeout=10
            ).json()
            self._note_error(key, interval, r1)
            c_hist = r1.get("data", {}).get("candles", [])
            c_intra = []
            if interval != "D":
                r2 = requests.get(
                    f"https://api.upstox.com/v3/historical-candle/intraday/{ikey}/{utype}/{uval}",
                    headers=self.headers, timeout=10
                ).json()
                c_intra = r2.get("data", {}).get("candles", [])
            rows = c_intra + c_hist
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(IST)
            df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").set_index("timestamp")

        if interval in ("3", "240") and not df.empty:
            rule = "3min" if interval == "3" else "240min"
            df = df.resample(rule, origin="start_day", offset="15min").agg({
                "open": "first", "high": "max", "low": "min",
                "close": "last", "volume": "sum", "oi": "last"
            }).dropna(subset=["close"])

        return df

    def get_breadth_changes(self) -> dict:
        out = {}
        for sym, _ in BREADTH_STOCKS:
            df_d = self.get_candles(sym, interval="D", days=6)
            if len(df_d) >= 2:
                prev_c = df_d["close"].iloc[-2]
                curr_c = df_d["close"].iloc[-1]
                out[sym] = (curr_c / prev_c - 1.0) * 100.0 if prev_c > 0 else np.nan
            else:
                out[sym] = np.nan
        return out

    def get_option_chain_metrics(self, atm_now: float, locked_atm_vol: float, oc_n: int, ov_n: int) -> dict:
        oc_n = clamp_strike_span(oc_n)
        ov_n = clamp_strike_span(ov_n)
        selected_exp = self.get_selected_expiry()

        oi_ce, oi_pe = {}, {}
        vol_ce, vol_pe = {}, {}
        oi_cnt = 0
        vol_cnt = 0
        ltp_map = {}
        ltp_n = max(oc_n, ov_n, 3)

        try:
            if self.broker == "DHAN":
                res = self.dhan.option_chain(under_security_id=int(self.inst["NIFTY_SPOT"]), under_exchange_segment="IDX_I", expiry=selected_exp)
                oc = res.get("data", {}).get("oc", {})

                for off in range(-oc_n, oc_n + 1):
                    k_str = f"{atm_now + off * PARAMS['optStep']:.6f}"
                    if k_str in oc:
                        c_oi = oc[k_str].get("ce", {}).get("oi", 0) or 0
                        p_oi = oc[k_str].get("pe", {}).get("oi", 0) or 0
                        if c_oi > 0: oi_cnt += 1
                        if p_oi > 0: oi_cnt += 1
                        oi_ce[off] = c_oi
                        oi_pe[off] = p_oi

                for off in range(-ov_n, ov_n + 1):
                    k_str = f"{locked_atm_vol + off * PARAMS['optStep']:.6f}"
                    if k_str in oc:
                        c_v = oc[k_str].get("ce", {}).get("volume", 0) or 0
                        p_v = oc[k_str].get("pe", {}).get("volume", 0) or 0
                        if c_v > 0: vol_cnt += 1
                        if p_v > 0: vol_cnt += 1
                        vol_ce[off] = c_v
                        vol_pe[off] = p_v

                for off in range(-ltp_n, ltp_n + 1):
                    k_val = atm_now + off * PARAMS["optStep"]
                    k_str = f"{k_val:.6f}"
                    if k_str in oc:
                        ltp_map[round(float(k_val), 2)] = {
                            "ce": oc[k_str].get("ce", {}).get("last_price", np.nan),
                            "pe": oc[k_str].get("pe", {}).get("last_price", np.nan)}

            elif self.broker == "UPSTOX":
                res = requests.get(
                    f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={selected_exp}",
                    headers=self.headers, timeout=10
                ).json()
                for row in res.get("data", []):
                    k = row.get("strike_price", 0)
                    c_md = row.get("call_options", {}).get("market_data", {})
                    p_md = row.get("put_options", {}).get("market_data", {})
                    if abs((k - atm_now) / PARAMS["optStep"]) <= ltp_n:
                        ltp_map[round(float(k), 2)] = {"ce": c_md.get("ltp", np.nan), "pe": p_md.get("ltp", np.nan)}

                    off_oi = int(round((k - atm_now) / PARAMS["optStep"]))
                    if -oc_n <= off_oi <= oc_n:
                        c_oi = c_md.get("oi", 0) or 0
                        p_oi = p_md.get("oi", 0) or 0
                        if c_oi > 0: oi_cnt += 1
                        if p_oi > 0: oi_cnt += 1
                        oi_ce[off_oi] = c_oi
                        oi_pe[off_oi] = p_oi

                    off_v = int(round((k - locked_atm_vol) / PARAMS["optStep"]))
                    if -ov_n <= off_v <= ov_n:
                        c_v = c_md.get("volume", 0) or 0
                        p_v = p_md.get("volume", 0) or 0
                        if c_v > 0: vol_cnt += 1
                        if p_v > 0: vol_cnt += 1
                        vol_ce[off_v] = c_v
                        vol_pe[off_v] = p_v
        except Exception as e:
            print(f"Option Chain fetch warning: {e}")

        if ltp_map:
            self.last_ltp_map = ltp_map  # paper trading fill ke liye latest option LTP

        oc_ce_sum = sum(oi_ce.values())
        oc_pe_sum = sum(oi_pe.values())
        oc_ok = (oi_cnt >= 4) and (oc_ce_sum > 0) and (oc_pe_sum > 0)
        oc_pcr = (oc_pe_sum / oc_ce_sum) if oc_ok else np.nan
        oc_c_arr = [oi_ce.get(i, 0) for i in range(0, oc_n + 1)]
        oc_p_arr = [oi_pe.get(-i, 0) for i in range(0, oc_n + 1)]
        oc_call_k = (atm_now + int(np.argmax(oc_c_arr)) * PARAMS["optStep"]) if (oc_ok and max(oc_c_arr) > 0) else np.nan
        oc_put_k = (atm_now - int(np.argmax(oc_p_arr)) * PARAMS["optStep"]) if (oc_ok and max(oc_p_arr) > 0) else np.nan

        vol_ce_sum = sum(vol_ce.values())
        vol_pe_sum = sum(vol_pe.values())
        vol_ok = (vol_cnt >= 4) and (vol_ce_sum > 0) and (vol_pe_sum > 0)
        vol_pcr = (vol_pe_sum / vol_ce_sum) if vol_ok else np.nan
        vol_sig = 0.0 if np.isnan(vol_pcr) else (1.0 if vol_pcr >= PARAMS["ovBull"] else (-1.0 if vol_pcr <= PARAMS["ovBear"] else 0.0))
        v_c_arr = [vol_ce.get(i, 0) for i in range(0, ov_n + 1)]
        v_p_arr = [vol_pe.get(-i, 0) for i in range(0, ov_n + 1)]
        vol_call_k = (locked_atm_vol + int(np.argmax(v_c_arr)) * PARAMS["optStep"]) if (vol_ok and max(v_c_arr) > 0) else np.nan
        vol_put_k = (locked_atm_vol - int(np.argmax(v_p_arr)) * PARAMS["optStep"]) if (vol_ok and max(v_p_arr) > 0) else np.nan

        return {
            "expiry": selected_exp, "ltpMap": ltp_map,
            "ocOk": oc_ok, "ocPcr": oc_pcr, "ocCallK": oc_call_k, "ocPutK": oc_put_k, "ocCnt": oi_cnt, "ocSpan": oc_n,
            "volOk": vol_ok, "volPcr": vol_pcr, "volSig": vol_sig,
            "volCeSum": vol_ce_sum, "volPeSum": vol_pe_sum,
            "volCallK": vol_call_k, "volPutK": vol_put_k, "volCnt": vol_cnt, "volSpan": ov_n
        }

    def place_option_order(self, side: str, strike: float, lots: int, action: str = "BUY", expiry_date: str = "") -> bool:
        self.last_order_info = {}
        if CONFIG.get("PAPER_TRADING", False) and CONFIG["RUN_MODE"] == "LIVE" and lots > 0:
            try:
                self.paper_order(side, strike, lots, action=action, expiry_date=expiry_date)
            except Exception as e:
                print(f"[Paper Order Error] {e}")
            return False  # paper mode me kabhi real broker order nahi jayega
        if not CONFIG["AUTO_PLACE_ORDER"] or lots <= 0 or CONFIG["RUN_MODE"] != "LIVE":
            return False
        qty = lots * PARAMS["optLot"]
        opt_type = "CE" if side == "CE" else "PE"
        exp = expiry_date or self.get_selected_expiry()
        print(f"EXECUTING LIVE {self.broker} {action} ORDER: NIFTY [{exp}] {int(strike)} {opt_type} ({PARAMS['strikeMode']}) | Lots: {lots} (Qty: {qty})")
        try:
            df_m = self.inst["_DF"]
            if self.broker == "DHAN":
                opt_df = df_m[
                    (df_m["SEM_EXM_EXCH_ID"] == "NSE") &
                    (df_m["SEM_INSTRUMENT_NAME"] == "OPTIDX") &
                    (df_m["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-")) &
                    (df_m["SEM_OPTION_TYPE"] == opt_type) &
                    (df_m["SEM_STRIKE_PRICE"] == float(strike)) &
                    (df_m["SEM_EXPIRY_DATE"].astype(str).str.startswith(exp))
                ]
                if not opt_df.empty:
                    sec_id = str(opt_df.iloc[0]["SEM_SMST_SECURITY_ID"])
                    txn = self.dhan.BUY if action == "BUY" else self.dhan.SELL
                    res_o = self.dhan.place_order(
                        security_id=sec_id,
                        exchange_segment=self.dhan.NSE_FNO,
                        transaction_type=txn,
                        quantity=qty,
                        order_type=self.dhan.MARKET,
                        product_type=self.dhan.INTRA,
                        price=0
                    )
                    self.last_order_info = self._dhan_fill_info(res_o, side, strike)
                    return self.last_order_info.get("src") != "ORDER_FAILED"
            elif self.broker == "UPSTOX":
                opt_df = df_m[
                    (df_m["segment"] == "NSE_FO") &
                    (df_m["name"] == "NIFTY") &
                    (df_m["instrument_type"] == opt_type) &
                    (df_m["strike_price"] == float(strike))
                ].copy()
                opt_df["exp_str"] = opt_df["expiry"].apply(lambda x: dt.datetime.fromtimestamp(x / 1000, IST).strftime("%Y-%m-%d"))
                opt_df = opt_df[opt_df["exp_str"] == exp]
                if not opt_df.empty:
                    ikey = opt_df.iloc[0]["instrument_key"]
                    payload = {
                        "quantity": qty,
                        "product": "I",
                        "validity": "DAY",
                        "price": 0,
                        "instrument_token": ikey,
                        "order_type": "MARKET",
                        "transaction_type": action,
                        "disclosed_quantity": 0,
                        "trigger_price": 0,
                        "is_amo": False
                    }
                    resp_o = requests.post("https://api.upstox.com/v2/order/place", json=payload, headers=self.headers, timeout=10)
                    self.last_order_info = self._upstox_fill_info(resp_o, side, strike)
                    return self.last_order_info.get("src") != "ORDER_FAILED"
        except Exception as e:
            print(f"[Order Placement Error] {e}")
        return False


# ==============================================================================
# 4B. DASHBOARD (nifty_dash.py): TABLES + CONSOLE + HTML CHART
# ==============================================================================
NAN = float("nan")
SECTOR_NAMES = list(SECTOR_MAP.keys())


def na(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def nz(x, d=0.0):
    return d if na(x) else x


def fmtG(g, flat=0.02):
    return "--" if na(g) else (("+" if g >= 0 else "") + f"{g:.2f}%")


def colG(g, flat):
    return "gray" if na(g) else ("green" if g > flat else ("red" if g < -flat else "gray"))


def pfTxt(gp, gl):
    return f"{gp / gl:.2f}" if gl > 0 else ("inf" if gp > 0 else "--")


def fmt_t(t, fmt="dd MMM HH:mm"):
    if t is None:
        return "--"
    m = {"dd/MM HH:mm": "%d/%m %H:%M", "dd MMM HH:mm": "%d %b %H:%M", "dd/MM": "%d/%m"}
    return pd.Timestamp(t).strftime(m.get(fmt, "%d %b %H:%M"))


def T(name, pos, rows, title=None, cols=2, enabled=True):
    return dict(name=name, pos=pos, rows=rows, title=title, cols=cols, enabled=enabled)


def build_tables(eng, o, D, vp, C):
    tabs = []
    unit = "%" if o.isPrem else "p"
    fl = C.flatPct

    rows = {}
    sd = C.showDetail

    def rLV(r, l, v, col):
        if r < 22 or sd:
            rows[r] = (l, v, col)

    pre = getattr(o, "preCE", False) or getattr(o, "preAlertPE", False)
    actCol = ("green" if o.act.startswith("BUY CE") else "red" if o.act.startswith("BUY PE") else
              "blue" if o.act.startswith("HOLD") else "orange" if (o.act.startswith("EXIT") or o.act.startswith("BOOK")) else "purple")
    actTxt = ("FINAL BUY CE" if o.fbCE else "FINAL BUY PE" if o.fbPE else "PRE-ALERT CE" if o.preCE else
              "PRE-ALERT PE" if o.preAlertPE else (o.act + (" " + o.plusTxt if o.entNow else "")).strip())
    actC = "blue" if (o.fbCE or o.fbPE) else ("orange" if pre else actCol)
    rLV(1, "ACTION", actTxt, actC)
    rLV(2, "Timeframe", "5m OK | " + o.modeTxt, "green")
    rLV(3, "3m / 5m / 15m", o.mtfTxt, "gray")
    sT = lambda x: "CE" if x == 1 else ("PE" if x == -1 else "-")
    rLV(4, "1h / 4h", sT(o.sideC) + " / " + sT(o.sideD), "gray")
    finCol = ("green" if o.fin == "CE BUY - HIGH PROB" else "red" if o.fin == "PE BUY - HIGH PROB" else
              "orange" if "medium" in o.fin else "maroon" if o.fin == "EXIT / AVOID" else "gray")
    rLV(5, "Signal", (o.fin + (" " + o.plusTxt if (o.sigCE or o.sigPE) else "")).strip(), finCol)
    brCol = ("green" if o.bullHi else "red" if o.bearHi else "lime" if o.bullMd else "maroon" if o.bearMd else "gray")
    scCol = "gray" if na(o.score) else ("green" if o.score >= C.hiTh else ("red" if o.score <= 100 - C.hiTh else "orange"))
    rLV(6, "Breadth", "N/A" if na(o.score) else f"{o.score:.0f} {o.brTxt}", scCol)
    rLV(7, "Entry (prem)" if o.isPrem else "Entry (price)", f"{o.shEn:.2f}" if o.shOn else "--", "blue")
    rLV(8, "Stop Loss", f"{o.shSl:.2f}" if o.shOn else "--", "red" if o.shOn else "gray")
    rLV(9, "Target 1", f"{o.shT1:.2f}" if o.shOn else "--", "green" if o.shOn else "gray")
    rLV(10, "Target 2", f"{o.shT2:.2f}" if o.shOn else "--", "green" if o.shOn else "gray")
    cE, pE = o.callEff, o.putEff
    if o.sideNow == 0:
        revTxt = "OI wall nahi" if (na(cE) and na(pE)) else "R " + ("--" if na(cE) else f"{cE:.0f}") + " / S " + ("--" if na(pE) else f"{pE:.0f}")
    else:
        revTxt = "OI wall nahi" if na(o.relK) else (("Resist " if o.sideNow == 1 else "Support ") + f"{o.relK:.0f}" +
                                                      (f" ~{o.relPrem:.1f}" if (o.isPrem and not na(o.relPrem)) else ""))
    rLV(11, "Reversal", revTxt, "gray" if (na(o.relK) and o.sideNow != 0) else "orange")
    ltpTxt = f"{o.close:.2f}" + ("" if na(o.pnlV) else f" | {'+' if o.pnlV >= 0 else ''}{o.pnlV:.1f}" + ("%" if o.isPrem else " pts"))
    rLV(12, "LTP / P&L", ltpTxt, "gray" if na(o.pnlV) else ("green" if o.pnlV >= 0 else "red"))
    rLV(13, "Lots", ("--" if not o.shOn else (f"0 lot: 1 lot risk Rs {o.lotRisk:.0f} > limit" if o.lots == 0 else f"{o.lots} lot / Rs {o.riskRs:.0f}")), "gray")
    rLV(14, "Kyu nahi?", o.why, "green" if o.why == "Signal OK" else "orange")
    lastSig = "Abhi tak nahi" if eng.lastSigT is None else f"{eng.lastSigTx} {fmt_t(eng.lastSigT)} ({eng.bar_idx - eng.lastSigBar} bar)"
    rLV(15, "Last signal", lastSig, "gray" if eng.lastSigTx == "" else ("green" if eng.lastSigTx.startswith("CE") else "red"))
    dirTxt = "Bullish" if o.mDir == 1 else ("Bearish" if o.mDir == -1 else "Neutral")
    rLV(16, "Trend since", f"{dirTxt} {fmt_t(eng.dirSince)} ({eng.bar_idx - eng.dirSinceBar} bar)",
        "green" if o.mDir == 1 else ("red" if o.mDir == -1 else "gray"))
    rLV(29, "ATM Strike", "-" if na(o.ocAtmNow) else f"{o.ocAtmNow:.0f}", "gray")
    rLV(22, "Bull / Bear score", f"{o.bull} / {o.bear} (of {o.maxC})", "gray")
    trTxt = "Bullish" if (o.ema9 > o.ema21 and o.close > o.ema50) else ("Bearish" if (o.ema9 < o.ema21 and o.close < o.ema50) else "Mixed")
    rLV(23, "EMA 9/21/50", trTxt, "green" if trTxt == "Bullish" else ("red" if trTxt == "Bearish" else "gray"))
    vwTxt = "N/A (no volume)" if not o.vwOk else ("Above" if o.close > o.vw else "Below")
    rLV(24, "VWAP", vwTxt, "gray" if not o.vwOk else ("green" if o.close > o.vw else "red"))
    rLV(25, "Supertrend", "Bullish" if o.sdir < 0 else "Bearish", "green" if o.sdir < 0 else "red")
    rLV(26, "RSI 14", f"{o.rsiV:.0f}", "green" if o.rsiV > 55 else ("red" if o.rsiV < 45 else "gray"))
    orTxt = "Forming" if not o.orDone else ("Break UP" if o.close > o.orH else ("Break DOWN" if o.close < o.orL else "Inside"))
    rLV(27, "Opening Range", orTxt, "green" if orTxt == "Break UP" else ("red" if orTxt == "Break DOWN" else "gray"))
    rLV(28, "Volume", "N/A" if not o.volOk else ("Surge" if o.volSurge else "Normal"), "green" if o.volSurge else "gray")

    optShow = (not o.isPrem) and o.shOn
    optEnU = C.optEntry if C.optEntry > 0 else o.optEnPx
    if optShow:
        dSlO = abs(o.shEn - o.shSl) * C.optDelta; dT1O = abs(o.shT1 - o.shEn) * C.optDelta; dT2O = abs(o.shT2 - o.shEn) * C.optDelta
        rows[18] = ("OPTION Entry", (f"{optEnU:.1f}" + (" (haath)" if C.optEntry > 0 else (" (locked)" if o.posSt != 0 else " (abhi)"))) if not na(optEnU)
                    else ("Symbol daalo (Settings)" if C.optSym == "" else "Option data nahi mila"), "blue")
        rows[19] = ("OPTION SL", f"{optEnU - dSlO:.1f} (-{dSlO:.1f})" if not na(optEnU) else f"-{dSlO:.1f} pts", "red")
        rows[20] = ("OPTION T1", f"{optEnU + dT1O:.1f} (+{dT1O:.1f})" if not na(optEnU) else f"+{dT1O:.1f} pts", "green")
        rows[21] = ("OPTION T2", f"{optEnU + dT2O:.1f} (+{dT2O:.1f})" if not na(optEnU) else f"+{dT2O:.1f} pts", "green")
    if (not o.isPrem) and C.optSym != "":
        rows[17] = ("OPTION LTP", ("Data nahi mila - symbol check" if na(o.optPx) else
                                   f"{o.optPx:.1f}" + (f" | {'+' if o.optPx >= optEnU else ''}{o.optPx - optEnU:.1f}" if (o.posSt != 0 and not na(optEnU)) else "")),
                    "red" if na(o.optPx) else "gray")
    rLV(30, f"ADX {C.adxLen}", "N/A" if na(o.adxV) else f"{o.adxV:.1f}" + (" trend OK" if o.adxOk else " sideways") + f" | D+ {o.diPl:.0f} D- {o.diMi:.0f}",
        "green" if o.adxOk else "orange")
    if C.wfOn:
        if eng.wSt != 0:
            wTxt = (("WATCH CE " if eng.wSt == 1 else "WATCH PE ") + f"bar {eng.bar_idx - eng.wBar}/{max(C.wfMax, C.wfMin)} (min {C.wfMin}) dip {abs(eng.wSigC - eng.wExt):.0f}"
                    + (f" | need > {eng.wSigC:.0f}" if C.wfRule[0].upper() == "B" else (f" | MA {C.wfF}/{C.wfS} cross wait" if C.wfRule[0].upper() == "D" else "")))
        elif o.posSt != 0 and not na(eng.fbEn):
            wTxt = ">>> FINAL BUY MIL GAYA <<< (trade chal rahi)"
        else:
            wTxt = "-- | " + eng.wLast
        wc = "green" if eng.wSt != 0 else ("blue" if (o.posSt != 0 and not na(eng.fbEn)) else "purple")
        rows[21.5] = ("WATCH / FINAL", wTxt, wc)
    if C.dgOn:
        rows[31 if sd else 22] = ("Daily 20MA", f"{o.dgTag} | PE {o.peScore}/5", o.dgBg)
    tabs.append(T("SIGNAL", C.posSig, [rows[k] for k in sorted(rows)], title="NIFTY OPT PRO"))

    lgG, lgR = "green", "red"
    L = []
    L.append((None, f"SIGNAL LOG  W {eng.winN} / L {eng.lossN}  Total {'+' if eng.totPnl >= 0 else ''}{eng.totPnl:.1f}{unit}", "navy"))
    L.append((None, f"CE {eng.wCE + eng.lCE} tr | W{eng.wCE} L{eng.lCE} | {'+' if eng.tCE >= 0 else ''}{eng.tCE:.1f}{unit} | PF {pfTxt(eng.gpCE, eng.glCE)}",
              "gray" if eng.wCE + eng.lCE == 0 else (lgG if eng.tCE >= 0 else lgR)))
    L.append((None, f"PE {eng.wPE + eng.lPE} tr | W{eng.wPE} L{eng.lPE} | {'+' if eng.tPE >= 0 else ''}{eng.tPE:.1f}{unit} | PF {pfTxt(eng.gpPE, eng.glPE)}",
              "gray" if eng.wPE + eng.lPE == 0 else (lgG if eng.tPE >= 0 else lgR)))
    L.append((None, f"ALL PF {pfTxt(eng.gpCE + eng.gpPE, eng.glCE + eng.glPE)} | Max DD -{eng.maxDD:.1f}{unit}", "gray"))
    for x in eng.lg:
        L.append((None, x, "gray" if x == "--" else (lgG if " +" in x else lgR)))
    tabs.append(T("LOG", C.posLg, L, cols=1, enabled=C.showLog))

    b = o.bex
    B = [("BREADTH 20", o.brTxt, brCol),
         ("Bull wt", "--" if na(b["upPct"]) else f"{b['upPct']:.1f}%", "green" if (not na(b["upPct"]) and b["upPct"] > b["dnPct"]) else "gray"),
         ("Bear wt", "--" if na(b["dnPct"]) else f"{b['dnPct']:.1f}%", "red" if (not na(b["dnPct"]) and b["dnPct"] > b["upPct"]) else "gray"),
         ("Up / Down", f"{b['nUp']} / {b['nDn']}", "green" if b["nUp"] > b["nDn"] else ("red" if b["nUp"] < b["nDn"] else "gray")),
         ("Top10 Up/Dn", "--" if na(b["up10"]) else f"{b['up10']:.0f}% / {b['dn10']:.0f}%",
          "green" if (not na(b["up10"]) and b["up10"] > b["dn10"]) else ("red" if (not na(b["up10"]) and b["up10"] < b["dn10"]) else "gray")),
         ("Impl Nifty", fmtG(b["impl"]), colG(b["impl"], fl)),
         ("Alignment", "--" if na(o.score) else ("ALIGNED" if o.aligned else "MIXED"), "green" if o.aligned else "gray"),
         ("Covered", f"{b['nOk']} stk {b['wTot']:.0f}%", "gray")]
    tabs.append(T("BREADTH", C.posBr, B))

    oi = o.oiScore
    ocol = "green" if oi > 0 else ("red" if oi < 0 else "gray")
    O = [("OI / PCR", f"OI BULLISH ({oi:.1f})" if oi > 0 else (f"OI BEARISH ({oi:.1f})" if oi < 0 else "OI NEUTRAL"), ocol),
         ("PCR 9 strike", "chain/settings se" if not o.pcrOn else f"{o.pcrEff:.2f}" + (" chain" if getattr(o, "ocOk", False) else " manual") +
          (" bull" if o.pcrS > 0 else (" bear" if o.pcrS < 0 else " neutral")), "green" if o.pcrS > 0 else ("red" if o.pcrS < 0 else "gray")),
         ("Call Wall", "chain/settings se" if na(o.callEff) else f"{o.callEff:.0f}" + ("" if na(o.callDist) else f" ({o.callDist:.1f}%)") + (" PAAS" if o.nearCall else ""),
          "red" if o.nearCall else "gray"),
         ("Put Wall", "chain/settings se" if na(o.putEff) else f"{o.putEff:.0f}" + ("" if na(o.putDist) else f" ({o.putDist:.1f}%)") + (" PAAS" if o.nearPut else ""),
          "green" if o.nearPut else "gray"),
         ("Wall range", "--" if (na(o.putEff) or na(o.callEff)) else f"S {o.putEff:.0f} - R {o.callEff:.0f}", "gray"),
         ("Futures OI", o.futTxt, "green" if o.futS > 0 else ("red" if o.futS < 0 else "gray")),
         ("Rujhan", "BULLISH (CE side)" if oi >= 1 else ("BEARISH (PE side)" if oi <= -1 else "NEUTRAL"), "green" if oi >= 1 else ("red" if oi <= -1 else "gray")),
         ("Chain data", o.ocStatus, "orange"),
         ("ATM (auto)", "--" if na(o.ocAtmNow) else f"{o.ocAtmNow:.0f} ({o.ocK0:.0f}-{o.ocK8:.0f})", "blue")]
    if C.ovOn:
        ovCol = "green" if o.ovS > 0 else ("red" if o.ovS < 0 else "gray")
        O += [("VOL PCR", "no data" if not o.ovOk else f"{o.ovPcr:.2f}" + (" bull" if o.ovS > 0 else (" bear" if o.ovS < 0 else " neutral")), ovCol if o.ovOk else "orange"),
              ("VOL C / P", f"C {o.vol.get('ce', 0) / 1e5:.1f}L P {o.vol.get('pe', 0) / 1e5:.1f}L" if o.ovOk else "--", "gray"),
              ("VOL Wall", "--" if (na(o.ovPutK) or na(o.ovCallK)) else f"S {o.ovPutK:.0f} R {o.ovCallK:.0f}", "gray"),
              ("VOL data", ("VOL PCR se" if o.ovOk else "source chuno") + (" F" if C.ovFeed else ""), "green" if o.ovOk else "orange")]
    tabs.append(T("OI", C.posOi, O))

    gs = o.gs
    LS = []
    for i in range(10):
        a, b2 = gs[i], gs[i + 10]
        LS.append((f"{a[0]} {a[1]:.1f}%", fmtG(a[2]), colG(a[2], fl), f"{b2[0]} {b2[1]:.1f}%", fmtG(b2[2]), colG(b2[2], fl)))
    tabs.append(T("STOCKS", C.posLs, LS, cols=4, enabled=C.showList))

    sc = o.sc
    scTh = C.scTh
    f_scTxt = lambda v: "--" if na(v) else (("+" if v >= 0 else "") + f"{v:.2f}%")
    f_scCol = lambda v: "gray" if na(v) else ("green" if v >= scTh else ("red" if v <= -scTh else "gray"))
    avg = sc["avg"]
    dv = sorted(range(15), key=lambda j: (-(avg[j] if not na(avg[j]) else -1000), j))
    av = sorted(range(15), key=lambda j: ((avg[j] if not na(avg[j]) else 1000), j))
    S = [("SECTOR", f"{sc['valid']} sector / 20 stk", "gray"), (f"BANKS ({sc['bkN']})", f_scTxt(sc["bk"]), f_scCol(sc["bk"]))]
    for r in range(3):
        si = dv[r]; ok = r < sc["valid"]
        S.append((f"STRONG {r + 1}", f"{SECTOR_NAMES[si]} {f_scTxt(avg[si])}" if ok else "--", f_scCol(avg[si] if ok else NAN)))
    for r in range(3):
        wi = av[r]; ok = r < sc["valid"] - 3
        S.append((f"WEAK {r + 1}", f"{SECTOR_NAMES[wi]} {f_scTxt(avg[wi])}" if ok else "--", f_scCol(avg[wi] if ok else NAN)))
    S.append(("FILTER", ("ON, data nahi" if sc["noData"] else f"ON CE {'OK' if sc['scCE'] else 'BLOCK'} PE {'OK' if sc['scPE'] else 'BLOCK'}") if C.scFeed else "OFF (sirf dikhata)",
              ("orange" if sc["noData"] else "blue") if C.scFeed else "gray"))
    tabs.append(T("SECTOR", C.scPos, S, enabled=C.scOn))
    SA = []
    for q in range(15):
        has = sc["cn"][q] > 0 and not na(avg[q])
        SA.append((SECTOR_NAMES[q] + (f" ({sc['cn'][q]})" if has else ""), f_scTxt(avg[q] if has else NAN), f_scCol(avg[q] if has else NAN)))
    tabs.append(T("SECTOR ALL", C.scPosA, SA, enabled=C.scAll))

    jTot = max(1, math.ceil(len(eng.jRows) / 15.0))
    page = eng.jRows[(C.jPg - 1) * 15:(C.jPg - 1) * 15 + 15]
    J = [(None, f"JOURNAL pg {C.jPg}/{jTot} | {len(eng.jRows)} trade since {fmt_t(eng.jFirst, 'dd/MM')} | M=MAE F=MFE FB=FinalBuy D=dip/bar", "navy")]
    J += [(None, x, "green" if " +" in x else "red") for x in page]
    tabs.append(T("JOURNAL", C.posJ, J, cols=1, enabled=C.jShow))

    def phTx(a, d):
        n = d["n"]
        return (f"{a} {n}tr W{(d['w'] * 100.0 / n if n > 0 else 0):.0f}% PF {pfTxt(d['g'], d['l'])} {'+' if d['q'] >= 0 else ''}{d['q']:.1f}",
                "gray" if n == 0 else ("green" if d["q"] >= 0 else "red"))
    p1 = "P1 " + fmt_t(pd.Timestamp(C.ph1S), "dd/MM"); p2 = "P2 " + fmt_t(pd.Timestamp(C.ph2S), "dd/MM")
    PH = [(None, f"PHASE-WISE (entry date se) | P2 end {fmt_t(pd.Timestamp(C.phE), 'dd/MM')}", "navy")]
    for a, k in ((p1 + " CE", "1C"), (p1 + " PE", "1P"), (p2 + " CE", "2C"), (p2 + " PE", "2P")):
        t, c = phTx(a, eng.ph[k]); PH.append((None, t, c))
    tabs.append(T("PHASE", C.posPh, PH, cols=1, enabled=C.phShow))

    nT = eng.winN + eng.lossN
    gpAll = eng.gpCE + eng.gpPE; glAll = eng.glCE + eng.glPE
    X = [(None, f"EXTRA STATS ({nT} trade since {fmt_t(eng.jFirst, 'dd/MM')})", "navy"),
         (None, f"Win% CE {(eng.wCE * 100.0 / (eng.wCE + eng.lCE)) if (eng.wCE + eng.lCE) > 0 else float('nan'):.0f} | PE "
                f"{(eng.wPE * 100.0 / (eng.wPE + eng.lPE)) if (eng.wPE + eng.lPE) > 0 else float('nan'):.0f} | All "
                f"{(eng.winN * 100.0 / nT) if nT > 0 else float('nan'):.0f}", "gray"),
         (None, f"Avg Win +{(gpAll / eng.winN) if eng.winN > 0 else float('nan'):.1f} | Avg Loss -{(glAll / eng.lossN) if eng.lossN > 0 else float('nan'):.1f}", "gray"),
         (None, f"Expectancy {(('+' if eng.totPnl >= 0 else '') + format(eng.totPnl / nT, '.1f')) if nT > 0 else '-'} per trade",
          "gray" if nT == 0 else ("green" if eng.totPnl >= 0 else "red")),
         (None, f"Max loss streak: {eng.maxConsL}", "gray"),
         (None, f"Winners MAE avg {(eng.sMaeW / eng.winN) if eng.winN > 0 else float('nan'):.0f} / max {eng.mMaeW:.0f} (SL idea)", "gray"),
         (None, f"Avg MFE {(eng.sMfe / nT) if nT > 0 else float('nan'):.0f}", "gray")]
    if C.wfOn:
        X += [(None, f"Watch {eng.wNsig} | Final Buy {eng.wNfin} | Nahi {eng.wNcan}", "gray"),
              (None, f"FINAL BUY se: {eng.fbN}tr W{(eng.fbW * 100.0 / eng.fbN) if eng.fbN > 0 else 0:.0f}% PF {pfTxt(eng.fbGp, eng.fbGl)} {'+' if eng.fbT >= 0 else ''}{eng.fbT:.1f}",
               ("green" if eng.fbT >= 0 else "red") if eng.fbN > 0 else "gray"),
              (None, f"Wahi trade signal se: {'+' if eng.fbOrg >= 0 else ''}{eng.fbOrg:.1f} | Bina FB {eng.noN}tr {'+' if eng.noT >= 0 else ''}{eng.noT:.1f}", "gray")]
    else:
        X += [(None, "Final Buy arrow OFF", "gray")]
    tabs.append(T("EXTRA STATS", C.posXs, X, cols=1, enabled=C.xsShow))

    gdCol = lambda n: "green" if n >= C.gdA else ("orange" if n >= C.gdB else "red")
    gdTxt = lambda n: "A" if n >= C.gdA else ("B" if n >= C.gdB else "C")
    G = [("SETUP CE", f"{gdTxt(o.gdCE)} {o.gdCE}/9", gdCol(o.gdCE)), ("CE weak", o.gdWC if o.gdWC else "-", "orange" if o.gdWC else "gray"),
         ("SETUP PE", f"{gdTxt(o.gdPE)} {o.gdPE}/9", gdCol(o.gdPE)), ("PE weak", o.gdWP if o.gdWP else "-", "orange" if o.gdWP else "gray")]
    tabs.append(T("GRADE", C.gdPos, G, enabled=C.gdShow))

    V = []
    if vp is not None:
        ok = vp.get("ok")
        if ok:
            sig = vp["sig"]
            V = [("VOL PCR", f"{vp['pcr']:.2f}" + (" bull" if sig > 0 else (" bear" if sig < 0 else " neutral")), "green" if sig > 0 else ("red" if sig < 0 else "gray")),
                 ("VOL C / P", f"C {vp['ce'] / 1e5:.1f}L P {vp['pe'] / 1e5:.1f}L", "gray"),
                 ("VOL Wall", "--" if (na(vp["putK"]) or na(vp["callK"])) else f"S {vp['putK']:.0f} R {vp['callK']:.0f}", "gray"),
                 ("ATM (lock)", f"{vp['ctr']:.0f} +-{C.vp_N}", "blue"),
                 ("VOL data", f"{vp['exp']:%y%m%d} {vp['cnt']}/{vp['total']}", "green"),
                 ("Spot / ATM src", f"{o.close:.1f} " + ("spot" if C.vp_useSpot else "chart"), "gray")]
        else:
            V = [("VOL PCR", "no data", "orange"), ("VOL data", (f"{pd.Timestamp(vp['exp']):%y%m%d} " if vp.get('exp') is not None else "-- ") + f"{vp.get('cnt')}/{vp.get('total')}", "orange")]
    tabs.append(T("VOL PCR", C.vp_pos, V, title="VOL PCR", enabled=C.vp_showTbl and bool(V)))
    return tabs


def render_console(tabs, only=None):
    out = []
    for t in tabs:
        if not t["enabled"] or (only and t["name"] not in only):
            continue
        out.append(f"+-- {t['name']} ({t['pos']}) " + "-" * 20)
        for r in t["rows"]:
            if t["cols"] == 1:
                out.append(f"| {r[0] if r[0] is not None else ''}{r[1] if r[0] is None else ''}")
            elif t["cols"] == 4:
                out.append(f"| {r[0]:<22} {r[1]:>8}   {r[3]:<22} {r[4]:>8}")
            else:
                out.append(f"| {r[0]:<16} {r[1]}")
    return "\n".join(out)


CSS_COL = {"green": "#1b8f4b", "red": "#c0392b", "gray": "#4a5568", "orange": "#d9822b", "blue": "#2563eb", "purple": "#7c3aed",
           "navy": "#1e2a52", "maroon": "#8a1c3c", "lime": "#65a30d", "teal": "#0f766e"}
POS_CSS = {"Top Left": "top:6px;left:6px;align-items:flex-start", "Top Center": "top:6px;left:50%;transform:translateX(-50%);align-items:center",
           "Top Right": "top:6px;right:70px;align-items:flex-end", "Middle Left": "top:50%;left:6px;transform:translateY(-50%);align-items:flex-start",
           "Middle Right": "top:50%;right:70px;transform:translateY(-50%);align-items:flex-end",
           "Bottom Left": "bottom:30px;left:6px;align-items:flex-start", "Bottom Center": "bottom:30px;left:50%;transform:translateX(-50%);align-items:center",
           "Bottom Right": "bottom:30px;right:70px;align-items:flex-end"}


def _clean(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def _html_table(t, fs):
    h = [f'<table class="t" style="font-size:{fs}px">']
    if t["title"]:
        h.append(f'<tr><th colspan="{2 if t["cols"] != 1 else 1}" style="background:{CSS_COL["navy"]}">{t["title"]}</th></tr>')
    for r in t["rows"]:
        if t["cols"] == 1:
            h.append(f'<tr><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td></tr>')
        elif t["cols"] == 4:
            h.append(f'<tr><td style="background:{CSS_COL["navy"]}">{_esc(r[0])}</td><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td>'
                     f'<td style="background:{CSS_COL["navy"]}">{_esc(r[3])}</td><td style="background:{CSS_COL[r[5]]}">{_esc(r[4])}</td></tr>')
        else:
            h.append(f'<tr><td style="background:{CSS_COL["navy"]}">{_esc(r[0])}</td><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td></tr>')
    h.append("</table>")
    return "".join(h)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html(tabs, eng, o, C, path):
    fs = {"tiny": 10, "small": 12, "normal": 14}.get(C.textSz, 10)
    f5 = o.f5.tail(300)
    off = 19800
    ts = lambda t: int(pd.Timestamp(t).timestamp()) + off
    candles = [dict(time=ts(i), open=_clean(float(r.o)), high=_clean(float(r.h)), low=_clean(float(r.l)), close=_clean(float(r.c))) for i, r in f5.iterrows()]
    t0 = f5.index[0]
    ev = [e for e in eng.events if e["t"] >= t0]
    marks = []
    lblOn = C.lblMode != "OFF" and (C.lblBars == 0 or True)
    for e in ev:
        k = e["k"]
        if k == "BUY CE" and C.showMk:
            marks.append(dict(time=ts(e["t"]), position="belowBar", color="#16a34a" if e.get("p", 0) < 2 else "#84cc16", shape="arrowUp", text=(e["text"].replace("\n", " ") if lblOn else "BUY CE")))
        elif k == "BUY PE" and C.showMk:
            marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#dc2626" if e.get("p", 0) < 2 else "#d946ef", shape="arrowDown", text=(e["text"].replace("\n", " ") if lblOn else "BUY PE")))
        elif k == "EXIT" and C.showMk:
            marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#16a34a" if e.get("win") else "#dc2626", shape="circle", text=e["text"] if lblOn else "EXIT"))
        elif k == "FINAL BUY CE" and C.wfArrow:
            marks.append(dict(time=ts(e["t"]), position="belowBar", color="#2563eb", shape="arrowUp", text="FB " + e["text"]))
        elif k == "FINAL BUY PE" and C.wfArrow:
            marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#2563eb", shape="arrowDown", text="FB " + e["text"]))
    if getattr(o, "preCE", False):
        marks.append(dict(time=ts(o.t_open), position="belowBar", color="#eab308", shape="square", text="PRE CE"))
    if getattr(o, "preAlertPE", False):
        marks.append(dict(time=ts(o.t_open), position="aboveBar", color="#eab308", shape="square", text="PRE PE"))
    marks.sort(key=lambda m: m["time"])
    hist = [h for h in eng.hist if h["t"] >= t0]

    def series(key):
        return [({"time": ts(h["t"]), "value": h[key]} if not na(h[key]) else {"time": ts(h["t"])}) for h in hist]
    lines = []
    if o.posSt != 0 and not na(o.posEn):
        lines += [dict(price=o.posEn, color="#2563eb", title="ENTRY %.1f" % o.posEn, style=0), dict(price=o.posSl, color="#dc2626", title="SL %.1f" % o.posSl, style=2),
                  dict(price=o.posT1, color="#16a34a", title="T1 %.1f" % o.posT1, style=2), dict(price=o.posT2, color="#16a34a", title="T2 %.1f" % o.posT2, style=2)]
        if not na(o.revPlot):
            lines.append(dict(price=o.revPlot, color="#f59e0b", title="REVERSAL %.1f" % o.revPlot, style=1))
    if not o.isPrem:
        if not na(o.callEff): lines.append(dict(price=o.callEff, color="#ef4444", title="CALL WALL %.0f" % o.callEff, style=1))
        if not na(o.putEff): lines.append(dict(price=o.putEff, color="#22c55e", title="PUT WALL %.0f" % o.putEff, style=1))
    payload = dict(candles=candles, marks=marks, lines=lines, en=series("en"), sl=series("sl"), t1=series("t1"), t2=series("t2"),
                   wf=series("wf"), ws=series("ws"), showMa=bool(C.wfMaShow))
    zones = {}
    for t in tabs:
        if t["enabled"] and t["rows"]:
            zones.setdefault(t["pos"], []).append(_html_table(t, fs))
    zhtml = "".join(f'<div class="z" style="{POS_CSS[p]}">{"".join(v)}</div>' for p, v in zones.items() if p in POS_CSS)
    title = f"NIFTY OPT PRO - {o.t_open:%d %b %H:%M}  close {o.close:.1f}"
    html = f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="20"><title>{title}</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>html,body{{margin:0;height:100%;background:#0b1020;color:#e5e7eb;font-family:Arial,sans-serif}}
#chart{{position:absolute;inset:0}}
.z{{position:absolute;display:flex;flex-direction:column;gap:4px;z-index:5;pointer-events:none;max-height:96%}}
.t{{border-collapse:collapse;color:#fff;opacity:.93}} .t td,.t th{{border:1px solid rgba(255,255,255,.35);padding:1px 5px;white-space:nowrap}}
#bar{{position:absolute;top:0;left:0;right:0;height:0;z-index:9}} #btn{{position:absolute;right:6px;top:6px;z-index:10;background:#1e2a52;color:#fff;border:1px solid #fff5;padding:3px 8px;cursor:pointer}}
</style></head><body><div id="chart"></div><button id="btn" onclick="document.querySelectorAll('.z').forEach(e=>e.style.display=e.style.display=='none'?'flex':'none')">Tables</button>
{zhtml}
<script>
const P={json.dumps(payload, allow_nan=False)};
const ch=LightweightCharts.createChart(document.getElementById('chart'),{{layout:{{background:{{color:'#0b1020'}},textColor:'#cbd5e1'}},
 grid:{{vertLines:{{color:'#1b2440'}},horzLines:{{color:'#1b2440'}}}},timeScale:{{timeVisible:true,secondsVisible:false}},rightPriceScale:{{borderColor:'#334155'}}}});
const cs=ch.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderVisible:false,wickUpColor:'#26a69a',wickDownColor:'#ef5350'}});
cs.setData(P.candles); cs.setMarkers(P.marks);
function ln(d,c,w){{const s=ch.addLineSeries({{color:c,lineWidth:w,priceLineVisible:false,lastValueVisible:false}}); s.setData(d); return s;}}
ln(P.en,'#2563eb',2); ln(P.sl,'#dc2626',2); ln(P.t1,'#16a34a',2); ln(P.t2,'#84cc16',1);
if(P.showMa){{ln(P.wf,'#f59e0b',1); ln(P.ws,'#a855f7',1);}}
P.lines.forEach(l=>cs.createPriceLine({{price:l.price,color:l.color,lineWidth:1,lineStyle:l.style,axisLabelVisible:true,title:l.title}}));
ch.timeScale().fitContent();
</script></body></html>'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ==============================================================================
# 5. COMPLETE STRATEGY ENGINE (LIVE REAL TRADE COUNTER + BACKTEST)
# ==============================================================================
class NiftyOptionProEngine:
    def __init__(self, broker: BrokerConnector, is_backtest: bool = False, bt_entry_mode: str = "ALL_SIGNALS"):
        self.broker = broker
        self.is_backtest = is_backtest
        self.bt_entry_mode = bt_entry_mode
        self.ovCtr = None
        self.bar_index = 0
        self.last_pre_alert_bar = -1

        self.real_trade_count = 0
        self.real_live_orders_sent = 0
        self.active_real_trade_id = ""
        self._load_existing_real_trade_count()

        self.posSt = 0
        self.posEn = np.nan
        self.posSl = np.nan
        self.posT1 = np.nan
        self.posT2 = np.nan
        self.posR = np.nan
        self.posMv = False
        self.t1Booked = False
        self.activeStrike = 0.0
        self.activeExpiry = ""
        self.activeLots = 0
        self.remainingLots = 0
        self.realizedTradePnl = 0.0
        self.lastExit = -1000
        self.armCE = True
        self.armPE = True

        self.trade_journal = []
        self.opt_provider = None       # backtest: OptionPriceProvider (run_backtest set karta hai)
        self._bt_partials = []         # backtest: T1 partial exits (ts, spot, lots)
        self.live_entry = None         # live/paper: entry order ka premium info
        self.live_exits = []           # live/paper: exit orders (lots, premium) list
        self._cur_vix_df = None
        self.logs = []
        self.winN = 0
        self.lossN = 0
        self.totPnl = 0.0
        self.gp = 0.0
        self.gl = 0.0
        self.eqC = 0.0
        self.eqPk = 0.0
        self.maxDD = 0.0
        self.entTx = ""
        self.entT = None
        self.entAdx = np.nan
        self.entSc = np.nan
        self.entProbCE = 50.0
        self.entProbPE = 50.0
        self.tkLo = np.nan
        self.tkHi = np.nan

        self.wSt = 0
        self.wBar = 0
        self.wSigC = np.nan
        self.wSl = np.nan
        self.wExt = np.nan
        self.wLast = "--"
        self.wCloses = []
        self.fbEn = np.nan
        self.wPendingSide = ""
        self.wPendingStrike = 0.0
        self.wPendingExpiry = ""
        self.wPendingLots = 0
        self.wPendingPlus = ""
        self.wPendingAdx = np.nan
        self.wPendingSc = np.nan
        self.wPendingProbCE = 50.0
        self.wPendingProbPE = 50.0

        self.events = []
        self.hist = []
        self.lastSigT = None
        self.lastSigTx = ""
        self.lastSigBar = 0
        self.dirSince = None
        self.dirSinceBar = 0
        self._prevDir = 0
        self.wCE = self.lCE = self.wPE = self.lPE = 0
        self.tCE = self.tPE = 0.0
        self.gpCE = self.glCE = self.gpPE = self.glPE = 0.0
        self.jRows = []
        self.jFirst = None
        self.ph = {k: dict(n=0, w=0, g=0.0, l=0.0, q=0.0) for k in ("1C", "1P", "2C", "2P")}
        self.maxConsL = 0
        self._curL = 0
        self.mMaeW = 0.0
        self.sMaeW = 0.0
        self.sMfe = 0.0
        self.fbN = self.fbW = 0
        self.fbGp = self.fbGl = self.fbT = self.fbOrg = 0.0
        self.noN = 0
        self.noT = 0.0
        self.wNsig = self.wNfin = self.wNcan = 0
        self.optEnPrem = np.nan
        self.last_o = None
        self.last_vp = None
        self._fb_now = 0

    @property
    def bar_idx(self):
        return self.bar_index

    @property
    def lg(self):
        return self.logs

    def _dash_stats(self, exit_ts, exit_px, exit_reason, pnl, sgn, mae, mfe, fb_pnl):
        win = pnl > 0
        if sgn == 1:
            if win:
                self.wCE += 1
                self.gpCE += pnl
            else:
                self.lCE += 1
                self.glCE += abs(pnl)
            self.tCE += pnl
        else:
            if win:
                self.wPE += 1
                self.gpPE += pnl
            else:
                self.lPE += 1
                self.glPE += abs(pnl)
            self.tPE += pnl
        if win:
            self.mMaeW = max(self.mMaeW, mae)
            self.sMaeW += mae
            self._curL = 0
        else:
            self._curL += 1
            self.maxConsL = max(self.maxConsL, self._curL)
        self.sMfe += mfe

        had_fb = not np.isnan(self.fbEn)
        if had_fb:
            self.fbN += 1
            self.fbOrg += pnl
            if not np.isnan(fb_pnl):
                self.fbT += fb_pnl
                if fb_pnl > 0:
                    self.fbW += 1
                    self.fbGp += fb_pnl
                else:
                    self.fbGl += abs(fb_pnl)
        else:
            self.noN += 1
            self.noT += pnl

        ent_t = self.entT if self.entT is not None else exit_ts
        if self.jFirst is None:
            self.jFirst = ent_t
        try:
            d0 = pd.Timestamp(ent_t).date()
            p1s = pd.Timestamp(DASH["ph1S"]).date()
            p2s = pd.Timestamp(DASH["ph2S"]).date()
            pe = pd.Timestamp(DASH["phE"]).date()
            key = "1" if (p1s <= d0 < p2s) else ("2" if (p2s <= d0 <= pe) else None)
            if key:
                ph = self.ph[key + ("C" if sgn == 1 else "P")]
                ph["n"] += 1
                ph["q"] += pnl
                if win:
                    ph["w"] += 1
                    ph["g"] += pnl
                else:
                    ph["l"] += abs(pnl)
        except Exception:
            pass

        dip = abs(self.wSigC - self.wExt) if (had_fb and not np.isnan(self.wSigC) and not np.isnan(self.wExt)) else np.nan
        row = f"{self.entTx} {pd.Timestamp(ent_t):%d/%m %H:%M} {exit_reason} {pnl:+.1f}p M{mae:.0f} F{mfe:.0f}"
        if had_fb and not np.isnan(fb_pnl):
            row += f" FB{fb_pnl:+.0f}"
        if not np.isnan(dip):
            row += f" D{dip:.0f}"
        self.jRows.insert(0, row)
        self.jRows = self.jRows[:300]
        self.events.append(dict(t=exit_ts, k="EXIT", text=f"{exit_reason} {pnl:+.0f}", win=win))

    def _dash_pre(self, entCE, entPE):
        if self.last_o is not None:
            self.last_o.preCE = bool(entCE)
            self.last_o.preAlertPE = bool(entPE)

    def _dash_capture(self, L):
        t5, t3, t15, t1h, t4h = L["t5"], L["t3"], L["t15"], L["t1h"], L["t4h"]
        br = L["br"]
        close = L["close"]
        bar_ts = L["bar_ts"]
        oc = L.get("oc_data") or {}
        step = PARAMS["optStep"]
        posOn = self.posSt != 0
        mDir = L["mDir"]
        entCE, entPE = L["entCE"], L["entPE"]
        score, hasBr = L["score"], L["hasBr"]
        callEff, putEff = L["callEff"], L["putEff"]
        atmNow = L["atmNow"]
        oc_span = L["oc_span"]
        ov_span = L["ov_span"]
        nan = np.nan
        s_txt = lambda x: "CE" if x == 1 else ("PE" if x == -1 else "-")

        if entCE:
            act = "BUY CE"
        elif entPE:
            act = "BUY PE"
        elif L.get("exitNow"):
            exr = L.get("exRes", "")
            act = ("BOOK " if exr in ("T1", "T2", "T1_FULL") else "EXIT ") + exr
        elif posOn:
            act = "HOLD CE" if self.posSt == 1 else "HOLD PE"
        else:
            act = "WAIT"

        if posOn:
            shOn, shEn, shSl, shT1, shT2 = True, self.posEn, self.posSl, self.posT1, self.posT2
        elif self.wSt != 0 and not np.isnan(self.wSigC):
            slD = L["slD"]
            shOn = True
            shEn, shSl = self.wSigC, self.wSl
            shT1 = self.wSigC + self.wSt * slD * PARAMS["rrT"]
            shT2 = self.wSigC + self.wSt * slD * (PARAMS["rrT"] + 1.0)
        else:
            shOn, shEn, shSl, shT1, shT2 = False, nan, nan, nan, nan
        pnlV = (self.posSt * (close - self.posEn)) if posOn else nan

        sideNow = self.posSt if posOn else mDir
        relK = callEff if sideNow == 1 else (putEff if sideNow == -1 else nan)
        callDist = ((callEff - close) / close * 100.0) if not np.isnan(callEff) else nan
        putDist = ((close - putEff) / close * 100.0) if not np.isnan(putEff) else nan

        ltp_map = oc.get("ltpMap") or {}
        if posOn:
            o_side, o_strike = self.posSt, self.activeStrike
        else:
            o_side = mDir
            o_strike = L["strikeCE"] if mDir == 1 else (L["strikePE"] if mDir == -1 else nan)
        optPx = nan
        if o_side != 0 and not np.isnan(o_strike):
            rec = ltp_map.get(round(float(o_strike), 2))
            if rec:
                v = rec.get("ce" if o_side == 1 else "pe", nan)
                try:
                    v = float(v)
                    optPx = v if (not np.isnan(v) and v > 0) else nan
                except Exception:
                    optPx = nan
        if posOn:
            if np.isnan(self.optEnPrem) and not np.isnan(optPx):
                self.optEnPrem = optPx
            optEnPx = self.optEnPrem
        else:
            self.optEnPrem = nan
            optEnPx = optPx

        ocOk = L["ocOk"]
        if ocOk:
            ocStatus = f"Chain OK ({oc.get('ocCnt', 0)} pts, +-{oc_span})"
        elif PARAMS["pcrIn"] > 0 or PARAMS["callWall"] > 0 or PARAMS["putWall"] > 0:
            ocStatus = "Manual settings se"
        else:
            ocStatus = "Chain data nahi"
        volPcrVal = L["volPcrVal"]
        volOk_pcr = L["volOk_pcr"]
        vol_sig = oc.get("volSig", 0.0) if volOk_pcr else 0.0

        dgS1, dgS2, dgUp, dgDn = L["dgS1"], L["dgS2"], L["dgUp"], L["dgDn"]
        dgTag = f"{PARAMS['dgD1']}d {dgS1:+.2f}% {PARAMS['dgD2']}d {dgS2:+.2f}% " + ("UP" if dgUp else ("DOWN" if dgDn else "FLAT"))
        dgBg = "green" if dgUp else ("red" if dgDn else "gray")

        g = L.get
        wkC = [n for n, bad in (("Late", g("rawLateCE")), ("ADX girta", not g("rawAr")), ("RSI hot", not g("rawRsiCE")),
                                ("Candle", not g("rawCdCE")), ("Vol", not g("rawVol")),
                                ("Level", g("pdhNear") or g("rdUpNear")), ("Open", not g("rawOpCE")),
                                ("VIX", not g("rawVxCE")), ("Time", g("tmBlkR"))) if bad]
        wkP = [n for n, bad in (("Late", g("rawLatePE")), ("ADX girta", not g("rawAr")), ("RSI low", not g("rawRsiPE")),
                                ("Candle", not g("rawCdPE")), ("Vol", not g("rawVol")),
                                ("Level", g("pdlNear") or g("rdDnNear")),
                                ("Open", PARAMS["peBelowOpen"] and not (close < g("today_open"))),
                                ("VIX", not g("rawVxPE")), ("Time", g("tmBlkR"))) if bad]

        bex = dict(upPct=br["upPct"], dnPct=br["dnPct"], nUp=br["nUpC"], nDn=br["nDnC"], up10=br["up10"],
                   dn10=br["dn10"], impl=br["impl"], nOk=br["nOk"], wTot=br["wTot"])
        sc = dict(avg=br["secAvgL"], cn=br["secCn"], valid=br["scValid"], bk=br["scBk"], bkN=br["bkN"],
                  noData=(br["scValid"] == 0), scCE=br["scCE"], scPE=br["scPE"])
        bullMd = hasBr and score >= 55 and not br["bullHi"]
        bearMd = hasBr and score <= 45 and not br["bearHi"]

        f5 = L["df_5m"][["open", "high", "low", "close"]].tail(300).copy()
        f5.columns = ["o", "h", "l", "c"]

        o = SimpleNamespace(
            act=act, entNow=bool(entCE or entPE), plusTxt=L["plusTxt"], fin=L["fin"], why=L["why"],
            modeTxt=f"{PARAMS['strikeMode']} / {PARAMS['exitMode']}",
            mtfTxt=f"{s_txt(t3['side'])} / {s_txt(t5['side'])} / {s_txt(t15['side'])}",
            sideC=t1h["side"], sideD=t4h["side"], mDir=mDir, sideNow=sideNow,
            sigCE=L["sigCE"], sigPE=L["sigPE"], fbCE=(self._fb_now == 1), fbPE=(self._fb_now == -1),
            preCE=False, preAlertPE=False,
            score=score, brTxt=br["brTxt"], bullHi=br["bullHi"], bearHi=br["bearHi"], bullMd=bullMd, bearMd=bearMd,
            aligned=br["aligned"], bex=bex, sc=sc, gs=br["gs"],
            posSt=self.posSt, posEn=self.posEn, posSl=self.posSl, posT1=self.posT1, posT2=self.posT2,
            shOn=shOn, shEn=shEn, shSl=shSl, shT1=shT1, shT2=shT2, pnlV=pnlV,
            lots=L["lots"], lotRisk=L["lotRisk"], riskRs=L["riskRs"], isPrem=(PARAMS["chartType"] != "Index/Fut"),
            close=close, t_open=bar_ts, f5=f5,
            relK=relK, relPrem=nan, revPlot=relK, callEff=callEff, putEff=putEff, callDist=callDist, putDist=putDist,
            nearCall=L["nearCall"], nearPut=L["nearPut"],
            oiScore=L["oiScore"], pcrEff=L["ocPcrVal"], pcrOn=(not np.isnan(L["ocPcrVal"])), pcrS=L["pcrS"],
            ocOk=ocOk, ovUseF=L["ovUseF"], futS=L["futS"], futTxt=L["futTxt"],
            ocAtmNow=atmNow, ocK0=atmNow - oc_span * step, ocK8=atmNow + oc_span * step, ocStatus=ocStatus,
            ovOk=volOk_pcr, ovPcr=volPcrVal, ovS=vol_sig,
            ovPutK=oc.get("volPutK", nan), ovCallK=oc.get("volCallK", nan),
            vol=({"ce": oc.get("volCeSum", 0), "pe": oc.get("volPeSum", 0)} if volOk_pcr else {}),
            optEnPx=optEnPx, optPx=optPx,
            bull=t5["bull"], bear=t5["bear"], maxC=t5["maxC"],
            ema9=t5["ema9"], ema21=t5["ema21"], ema50=t5["ema50"], rsiV=t5["rsi"], sdir=t5["sdir"],
            vw=t5["vwap"], vwOk=t5["vwOk"], orDone=t5["orDone"], orH=t5["orH"], orL=t5["orL"],
            volOk=L["volOk"], volSurge=bool(L["volOk"] and L["vol"] >= 1.5 * L["volAvg"]),
            adxV=t5["adx"], adxOk=L["adxOk"], diPl=t5["diPl"], diMi=t5["diMi"],
            dgTag=dgTag, dgBg=dgBg, peScore=L["peScore"],
            gdCE=L["gdCE"], gdPE=L["gdPE"], gdWC=", ".join(wkC), gdWP=", ".join(wkP),
        )
        self.last_o = o

        if PARAMS["ovOn"]:
            try:
                exp_ts = pd.Timestamp(L["selected_exp"])
            except Exception:
                exp_ts = pd.Timestamp(bar_ts)
            self.last_vp = dict(ok=bool(volOk_pcr), sig=vol_sig, pcr=volPcrVal, ce=oc.get("volCeSum", 0),
                                pe=oc.get("volPeSum", 0), putK=oc.get("volPutK", nan), callK=oc.get("volCallK", nan),
                                ctr=(self.ovCtr if self.ovCtr is not None else atmNow), exp=exp_ts,
                                cnt=oc.get("volCnt", 0), total=2 * (2 * ov_span + 1))
        else:
            self.last_vp = None

        self.hist.append(dict(
            t=bar_ts,
            en=self.posEn if posOn else nan, sl=self.posSl if posOn else nan,
            t1=self.posT1 if posOn else nan, t2=self.posT2 if posOn else nan,
            wf=g("smaF", nan) if self.wSt != 0 else nan, ws=g("smaS", nan) if self.wSt != 0 else nan))
        self.hist = self.hist[-1500:]
        self.events = self.events[-800:]

    def render_dashboard(self, path=None, console=None):
        if not CONFIG.get("DASH_ON", True) or self.last_o is None:
            return
        try:
            C = SimpleNamespace(**{**PARAMS, **DASH, "vp_N": PARAMS["ovN"]})
            tabs = build_tables(self, self.last_o, None, self.last_vp, C)
            show_c = CONFIG.get("DASH_CONSOLE_TABLES", False) if console is None else console
            if show_c:
                print(render_console(tabs))
            render_html(tabs, self, self.last_o, C, path or CONFIG.get("DASH_HTML_PATH", "dashboard.html"))
        except Exception as exc:
            print(f"[Dashboard Error] {exc}")
            traceback.print_exc()

    def _load_existing_real_trade_count(self):
        if self.is_backtest:
            return
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        if os.path.exists(csv_file):
            try:
                df_ex = pd.read_csv(csv_file)
                self.real_trade_count = len(df_ex)
                if "OrderPlaced" in df_ex.columns:
                    self.real_live_orders_sent = int(df_ex["OrderPlaced"].sum())
            except Exception:
                pass

    def _order(self, side, strike, lots, action="BUY", expiry_date=""):
        """Broker order + option premium capture (live/paper). Backtest me sirf pass-through."""
        ok = self.broker.place_option_order(side, strike, lots, action=action, expiry_date=expiry_date)
        if self.is_backtest or lots <= 0:
            return ok
        try:
            info = dict(getattr(self.broker, "last_order_info", {}) or {})
            if not info:  # order nahi gaya (signal-only mode): option chain ka LTP dikhao
                ltp = self.broker._paper_ltp(side, strike)
                info = {"price": (None if ltp != ltp else float(ltp)), "src": "CHAIN_LTP"}
            info["lots"] = lots
            if action == "BUY":
                self.live_entry = info
                self.live_exits = []
            else:
                self.live_exits.append(info)
            if not CONFIG.get("PAPER_TRADING", False):
                px = info.get("price")
                px_txt = f"Rs {px:.2f}" if px else "price nahi mila"
                tag = "ORDER SENT" if ok else "SIGNAL ONLY (order nahi gaya)"
                self.alert(f"[{tag}] {action} {fmt_contract(side, strike, expiry_date)} | Lots {lots} (Qty {lots * PARAMS['optLot']}) @ premium {px_txt} ({info.get('src', 'NA')})")
        except Exception as e:
            print(f"[Premium Capture Error] {e}")
        return ok

    def _live_leg_summary(self) -> dict:
        e = self.live_entry or {}
        ep = e.get("price")
        out = {"EntryPremium": (round(ep, 2) if ep else None), "ExitPremium": None, "GrossPnL_Rs": None,
               "PremiumSrc": e.get("src", "NA"), "exit_orders": len(self.live_exits)}
        tot_l = sum(x.get("lots", 0) for x in self.live_exits)
        if tot_l > 0 and all(x.get("price") for x in self.live_exits):
            out["ExitPremium"] = round(sum(x["price"] * x["lots"] for x in self.live_exits) / tot_l, 2)
            if ep:
                out["GrossPnL_Rs"] = round(sum((x["price"] - ep) * x["lots"] * PARAMS["optLot"] for x in self.live_exits), 2)
            out["PremiumSrc"] = "/".join(sorted({e.get("src", "NA")} | {x.get("src", "NA") for x in self.live_exits}))
        return out

    def _premium_fields(self, exit_ts, exit_px, sgn) -> dict:
        """Journal ke liye: Contract, ExpiryDate, Entry/Exit premium (Rs), Gross/Fees/Net P&L (Rs)."""
        side = "CE" if sgn == 1 else "PE"
        out = {k: None for k in ("Contract", "ExpiryDate", "ExpiryDateSrc", "EntryPremium", "ExitPremium",
                                 "PremiumSrc", "GrossPnL_Rs", "Fees_Rs", "NetPnL_Rs")}
        fee = float(CONFIG.get("PAPER_BROKERAGE_PER_ORDER", 20.0))
        try:
            if self.is_backtest:
                ref = self.entT if self.entT is not None else exit_ts
                exp_date, esrc = self.broker.resolve_expiry_date(ref)
                out["ExpiryDate"], out["ExpiryDateSrc"] = exp_date, esrc
                out["Contract"] = fmt_contract(side, self.activeStrike, exp_date)
                if self.opt_provider is None or self.entT is None:
                    return out
                vdf = self._cur_vix_df

                def _vix_at(t):
                    if vdf is None or len(vdf) == 0:
                        return float("nan")
                    sub = vdf[vdf.index <= t]
                    return float(sub["close"].iloc[-1]) if len(sub) else float("nan")

                ep, s1 = self.opt_provider.price_at(side, self.activeStrike, exp_date, self.entT, self.posEn, _vix_at(self.entT))
                legs = [(p["ts"], p["spot"], p["lots"]) for p in self._bt_partials]
                if self.remainingLots > 0 or not legs:
                    legs.append((exit_ts, exit_px, self.remainingLots if self.remainingLots > 0 else self.activeLots))
                gross, wsum, lsum, srcs, ok = 0.0, 0.0, 0, {s1}, (ep == ep)
                for (t, sp, l) in legs:
                    xp, s2 = self.opt_provider.price_at(side, self.activeStrike, exp_date, t, sp, _vix_at(t))
                    srcs.add(s2)
                    if xp != xp or ep != ep:
                        ok = False
                        continue
                    gross += (xp - ep) * l * PARAMS["optLot"]
                    wsum += xp * l
                    lsum += l
                if ep == ep:
                    out["EntryPremium"] = round(ep, 2)
                out["PremiumSrc"] = "/".join(sorted(srcs)) if ok else "NA"
                if ok and lsum > 0:
                    fees = fee * (1 + len(legs))
                    out["ExitPremium"] = round(wsum / lsum, 2)
                    out["GrossPnL_Rs"] = round(gross, 2)
                    out["Fees_Rs"] = round(fees, 2)
                    out["NetPnL_Rs"] = round(gross - fees, 2)
            else:
                s = self._live_leg_summary()
                out["ExpiryDate"], out["ExpiryDateSrc"] = self.activeExpiry, "BROKER"
                out["Contract"] = fmt_contract(side, self.activeStrike, self.activeExpiry)
                out["EntryPremium"], out["ExitPremium"] = s["EntryPremium"], s["ExitPremium"]
                out["PremiumSrc"], out["GrossPnL_Rs"] = s["PremiumSrc"], s["GrossPnL_Rs"]
                if CONFIG.get("PAPER_TRADING", False) and s["GrossPnL_Rs"] is not None:
                    fees = fee * (1 + s["exit_orders"])
                    out["Fees_Rs"], out["NetPnL_Rs"] = round(fees, 2), round(s["GrossPnL_Rs"] - fees, 2)
        except Exception as e:
            print(f"[Premium Fields Error] {e}")
        return out

    def _log_real_trade_entry(self, bar_ts: dt.datetime, side: str, strike: float, expiry: str, lots: int, spot_px: float, prob: float, order_sent: bool):
        if self.is_backtest:
            return
        self.real_trade_count += 1
        if order_sent:
            self.real_live_orders_sent += 1
        self.active_real_trade_id = f"RT-{bar_ts.strftime('%Y%m%d')}-{self.real_trade_count}"
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        row = {
            "TradeID": self.active_real_trade_id,
            "Date": bar_ts.strftime("%Y-%m-%d"),
            "EntryTime": bar_ts.strftime("%H:%M:%S"),
            "Contract": fmt_contract(side, strike, expiry),
            "StrikeMode": PARAMS["strikeMode"],
            "Expiry": expiry,
            "Lots": lots,
            "Qty": lots * PARAMS["optLot"],
            "EntryPremium": ((self.live_entry or {}).get("price")),
            "ExitPremium": np.nan,
            "GrossPnL_Rs": np.nan,
            "PremiumSrc": ((self.live_entry or {}).get("src", "NA")),
            "EntrySpot": round(spot_px, 2),
            "ExitTime": "",
            "ExitSpot": np.nan,
            "ExitReason": "",
            "PnL_Pts": 0.0,
            "OI_Prob%": round(prob, 1),
            "OrderPlaced": order_sent,
            "Status": "OPEN"
        }
        df_new = pd.DataFrame([row])
        if os.path.exists(csv_file):
            df_old = pd.read_csv(csv_file)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_all = df_new
        df_all.to_csv(csv_file, index=False)

    def _log_real_trade_exit(self, exit_ts: dt.datetime, exit_px: float, exit_reason: str, pnl_pts: float):
        if self.is_backtest or not self.active_real_trade_id:
            return
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        if os.path.exists(csv_file):
            try:
                df_all = pd.read_csv(csv_file)
                mask = df_all["TradeID"] == self.active_real_trade_id
                if mask.any():
                    df_all = df_all.astype(object)  # empty columns float64 aa jaate hain; text likhne par error na aaye
                    _s = self._live_leg_summary()
                    for _c in ("EntryPremium", "ExitPremium", "GrossPnL_Rs", "Qty"):
                        if _c not in df_all.columns:
                            df_all[_c] = np.nan
                    if "PremiumSrc" not in df_all.columns:
                        df_all["PremiumSrc"] = ""
                    for _c in ("EntryPremium", "ExitPremium", "GrossPnL_Rs"):
                        if _s.get(_c) is not None:
                            df_all.loc[mask, _c] = _s[_c]
                    df_all.loc[mask, "PremiumSrc"] = str(_s.get("PremiumSrc", "NA"))
                    df_all.loc[mask, "ExitTime"] = exit_ts.strftime("%H:%M:%S")
                    df_all.loc[mask, "ExitSpot"] = round(exit_px, 2)
                    df_all.loc[mask, "ExitReason"] = exit_reason
                    df_all.loc[mask, "PnL_Pts"] = round(pnl_pts, 2)
                    df_all.loc[mask, "Status"] = "CLOSED"
                    df_all.to_csv(csv_file, index=False)
            except Exception as e:
                print(f"[Real Trade Journal Error] exit update fail: {e}")
        self.active_real_trade_id = ""

    def alert(self, text: str):
        if self.is_backtest:
            return
        print(text)
        tok, cid = CONFIG["TELEGRAM_BOT_TOKEN"], CONFIG["TELEGRAM_CHAT_ID"]
        if tok and cid:
            try:
                requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": text}, timeout=5)
            except Exception:
                pass

    def manual_exit_now(self, current_price: float, bar_ts: dt.datetime, reason: str = "MANUAL_EXIT"):
        if self.posSt == 0:
            print("Koi active position nahi hai.")
            return
        sgn = 1 if self.posSt == 1 else -1
        side_str = "CE" if self.posSt == 1 else "PE"
        rem_ratio = (self.remainingLots / self.activeLots) if self.activeLots > 0 else 1.0
        final_pnl = self.realizedTradePnl + sgn * (current_price - self.posEn) * rem_ratio

        self.broker.paper_reason = reason
        if self.remainingLots > 0:
            self._order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)

        self._record_closed_trade(bar_ts, current_price, reason, final_pnl)
        self.posSt = 0
        self.posMv = False
        self.t1Booked = False
        self.remainingLots = 0
        self.realizedTradePnl = 0.0
        self.lastExit = self.bar_index

    def _record_closed_trade(self, exit_ts: dt.datetime, exit_px: float, exit_reason: str, pnl_pts: float):
        sgn = 1 if self.posSt == 1 else -1
        mae = (self.posEn - self.tkLo) if sgn == 1 else (self.tkHi - self.posEn)
        mfe = (self.tkHi - self.posEn) if sgn == 1 else (self.posEn - self.tkLo)

        if pnl_pts > 0:
            self.winN += 1
            self.gp += pnl_pts
        else:
            self.lossN += 1
            self.gl += abs(pnl_pts)

        self.totPnl += pnl_pts
        self.eqC += pnl_pts
        self.eqPk = max(self.eqPk, self.eqC)
        self.maxDD = max(self.maxDD, self.eqPk - self.eqC)

        fb_pnl = (sgn * (exit_px - self.fbEn)) if not np.isnan(self.fbEn) else np.nan
        ent_prob = self.entProbCE if sgn == 1 else self.entProbPE
        _pf = self._premium_fields(exit_ts, exit_px, sgn)
        self.trade_journal.append({
            "EntryTime": self.entT.strftime("%Y-%m-%d %H:%M") if self.entT else "",
            "ExitTime": exit_ts.strftime("%Y-%m-%d %H:%M"),
            "Signal": self.entTx,
            "Contract": _pf["Contract"],
            "Strike": f"{int(self.activeStrike)} ({PARAMS['strikeMode']})",
            "Expiry": self.activeExpiry,
            "ExpiryDate": _pf["ExpiryDate"],
            "ExpiryDateSrc": _pf["ExpiryDateSrc"],
            "Lots": self.activeLots,
            "Qty": self.activeLots * PARAMS["optLot"],
            "EntryPremium": _pf["EntryPremium"],
            "ExitPremium": _pf["ExitPremium"],
            "PremiumSrc": _pf["PremiumSrc"],
            "GrossPnL_Rs": _pf["GrossPnL_Rs"],
            "Fees_Rs": _pf["Fees_Rs"],
            "NetPnL_Rs": _pf["NetPnL_Rs"],
            "EntryPx": round(self.posEn, 2),
            "ExitPx": round(exit_px, 2),
            "ExitReason": exit_reason,
            "PnL_Pts": round(pnl_pts, 2),
            "FB_PnL_Pts": round(fb_pnl, 2) if not np.isnan(fb_pnl) else None,
            "OI_Prob%": round(ent_prob, 1),
            "MAE": round(mae, 1),
            "MFE": round(mfe, 1),
            "ADX": round(self.entAdx, 1) if not np.isnan(self.entAdx) else 0,
            "Breadth": round(self.entSc, 1) if not np.isnan(self.entSc) else 0,
        })

        self._dash_stats(exit_ts, exit_px, exit_reason, pnl_pts, sgn, mae, mfe, fb_pnl)
        self._log_real_trade_exit(exit_ts, exit_px, exit_reason, pnl_pts)
        self._bt_partials = []
        self.live_entry = None
        self.live_exits = []
        log_line = f"{self.entTx} {self.entT.strftime('%d/%m %H:%M')} {exit_reason} {pnl_pts:+.1f}p P:{ent_prob:.0f}% A{self.entAdx:.0f} B{self.entSc:.0f}"
        self.logs.insert(0, log_line)
        self.logs = self.logs[:5]
        self.alert(f"EXIT {self.entTx} ({int(self.activeStrike)} {PARAMS['strikeMode']}) @ {exit_px:.1f} ({exit_reason}) | Net P&L: {pnl_pts:+.1f} pts | Total Real Trades: {self.real_trade_count}")

    def eval_timeframe(self, df: pd.DataFrame, is_5m: bool = False) -> dict:
        c_s = df["close"]
        ema9 = calc_ema(c_s, 9)
        ema21 = calc_ema(c_s, 21)
        ema50 = calc_ema(c_s, 50)
        rsi = calc_rsi(c_s, 14)
        sdir = calc_supertrend(df, 3.0, 10)
        vw = calc_vwap(df)
        diPl, diMi, adxV = calc_dmi(df, PARAMS["adxLen"])

        c = c_s.iloc[-1]
        e9, e21, e50 = ema9.iloc[-1], ema21.iloc[-1], ema50.iloc[-1]
        r = rsi.iloc[-1]
        sd = sdir.iloc[-1]
        v = vw.iloc[-1]
        vwOk = (not np.isnan(v)) and v > 0

        bull = (1 if (e9 > e21 and c > e50) else 0) + (1 if (vwOk and c > v) else 0) + (1 if sd < 0 else 0) + (1 if r > 55 else 0)
        bear = (1 if (e9 < e21 and c < e50) else 0) + (1 if (vwOk and c < v) else 0) + (1 if sd > 0 else 0) + (1 if r < 45 else 0)

        orTxt = "N/A"
        orH = orL = np.nan
        orDone = False
        if is_5m:
            today = df.index[-1].date()
            t_df = df[df.index.date == today]
            dayBar = len(t_df)
            orH = t_df["high"].iloc[:PARAMS["orBars"]].max() if len(t_df) > 0 else np.nan
            orL = t_df["low"].iloc[:PARAMS["orBars"]].min() if len(t_df) > 0 else np.nan
            orDone = dayBar > PARAMS["orBars"]

            bull += (1 if (orDone and c > orH) else 0)
            bear += (1 if (orDone and c < orL) else 0)
            orTxt = "Forming" if not orDone else ("Break UP" if c > orH else ("Break DOWN" if c < orL else "Inside"))

            maxC = 4 + (1 if vwOk else 0)
            needE = min(PARAMS["needN"], maxC)
        else:
            maxC = 3 + (1 if vwOk else 0)
            needE = min(PARAMS["mtfNeed"], maxC)

        side = 1 if (bull >= needE and bull > bear) else (-1 if (bear >= needE and bear > bull) else 0)
        arN = PARAMS["arN"]
        adx_prev = adxV.iloc[-1 - arN] if len(adxV) > arN else np.nan

        return {
            "side": side, "bull": bull, "bear": bear, "maxC": maxC, "needE": needE,
            "close": c, "ema9": e9, "ema21": e21, "ema50": e50, "rsi": r, "sdir": sd,
            "vwap": v, "vwOk": vwOk, "orTxt": orTxt, "orH": orH, "orL": orL, "orDone": orDone,
            "diPl": diPl.iloc[-1], "diMi": diMi.iloc[-1], "adx": adxV.iloc[-1], "adxPrev": adx_prev
        }

    def eval_breadth_and_sectors(self, changes: dict) -> dict:
        wTot = wUp = wDn = wCt = 0.0
        w10Tot = w10Up = w10Dn = 0.0
        nUpC = nDnC = nOkC = 0

        sec_ws = {k: 0.0 for k in SECTOR_MAP}
        sec_wg = {k: 0.0 for k in SECTOR_MAP}
        sec_cn = {k: 0 for k in SECTOR_MAP}
        bkW = bkG = 0.0
        bkN = 0

        for idx, (sym, wt) in enumerate(BREADTH_STOCKS):
            g = changes.get(sym, np.nan)
            if not np.isnan(g):
                nOkC += 1
                wTot += wt
                wCt += g * wt
                if g > PARAMS["flatPct"]:
                    wUp += wt
                    nUpC += 1
                elif g < -PARAMS["flatPct"]:
                    wDn += wt
                    nDnC += 1

                if idx < 10:
                    w10Tot += wt
                    if g > PARAMS["flatPct"]: w10Up += wt
                    elif g < -PARAMS["flatPct"]: w10Dn += wt

                if wt > 0:
                    for sname, members in SECTOR_MAP.items():
                        if sym in members:
                            sec_ws[sname] += wt
                            sec_wg[sname] += wt * g
                            sec_cn[sname] += 1
                    if sym in BANK_STOCKS:
                        bkW += wt
                        bkG += wt * g
                        bkN += 1

        upPct = (wUp / wTot * 100.0) if wTot > 0 else np.nan
        dnPct = (wDn / wTot * 100.0) if wTot > 0 else np.nan
        up10Pct = (w10Up / w10Tot * 100.0) if w10Tot > 0 else np.nan
        cntPct = (nUpC / (nUpC + nDnC) * 100.0) if (nUpC + nDnC) > 0 else 50.0
        impl = (wCt / wTot) if wTot > 0 else np.nan
        implPct = np.clip(50.0 + impl / PARAMS["implRef"] * 50.0, 0.0, 100.0) if not np.isnan(impl) else np.nan

        score = (upPct * 0.45 + up10Pct * 0.25 + cntPct * 0.10 + implPct * 0.20) if not np.isnan(upPct) else np.nan
        aligned = (not np.isnan(score)) and ((upPct > 50 and up10Pct > 50 and cntPct > 50) or (upPct < 50 and up10Pct < 50 and cntPct < 50))
        bullHi = (not np.isnan(score)) and score >= PARAMS["hiTh"] and aligned
        bearHi = (not np.isnan(score)) and score <= (100.0 - PARAMS["hiTh"]) and aligned

        brTxt = "NO DATA" if np.isnan(score) else ("CE HIGH" if bullHi else ("PE HIGH" if bearHi else ("CE medium" if score >= 55 else ("PE medium" if score <= 45 else "NO TRADE"))))

        sec_avg = {k: (sec_wg[k] / sec_ws[k]) if (sec_cn[k] > 0 and sec_ws[k] > 0) else np.nan for k in SECTOR_MAP}
        scBk = (bkG / bkW) if (bkN > 0 and bkW > 0) else np.nan
        scValid = sum(1 for v in sec_avg.values() if not np.isnan(v))

        h0, h1, h2 = sec_avg["Financial Svc"], sec_avg["Oil & Gas"], sec_avg["IT"]
        scUpN = sum(1 for v in (h0, h1, h2) if not np.isnan(v) and v >= PARAMS["scTh"])
        scDnN = sum(1 for v in (h0, h1, h2) if not np.isnan(v) and v <= -PARAMS["scTh"])

        scCE = (not PARAMS["scFeed"]) or (scValid == 0) or (scUpN >= PARAMS["scNeed"] and (not PARAMS["scBankOk"] or np.isnan(scBk) or scBk > -PARAMS["scTh"]))
        scPE = (not PARAMS["scFeed"]) or (scValid == 0) or (scDnN >= PARAMS["scNeed"] and (not PARAMS["scBankOk"] or np.isnan(scBk) or scBk < PARAMS["scTh"]))

        return {
            "score": score, "brTxt": brTxt, "bullHi": bullHi, "bearHi": bearHi,
            "upPct": upPct, "dnPct": dnPct, "nUpC": nUpC, "nDnC": nDnC, "impl": impl,
            "secAvg": sec_avg, "scBk": scBk, "scCE": scCE, "scPE": scPE,
            "up10": up10Pct, "dn10": ((w10Dn / w10Tot * 100.0) if w10Tot > 0 else np.nan),
            "nOk": nOkC, "wTot": wTot, "aligned": aligned, "bkN": bkN, "scValid": scValid,
            "secAvgL": [sec_avg[k] for k in SECTOR_MAP], "secCn": [sec_cn[k] for k in SECTOR_MAP],
            "gs": [(sym, wt, changes.get(sym, np.nan)) for sym, wt in BREADTH_STOCKS],
        }

    def calc_oi_and_vol_probability(self, oc_pcr, vol_pcr, fut_s, near_call, near_put, breadth_score):
        oi_norm = np.clip((oc_pcr - 1.0) / 0.35, -1.0, 1.0) if not np.isnan(oc_pcr) else 0.0
        vol_norm = np.clip((vol_pcr - 1.0) / 0.40, -1.0, 1.0) if not np.isnan(vol_pcr) else 0.0
        fut_norm = np.clip(fut_s, -1.0, 1.0) if PARAMS["futOiOn"] else 0.0
        br_norm = np.clip((breadth_score - 50.0) / 30.0, -1.0, 1.0) if not np.isnan(breadth_score) else 0.0

        raw_bias = (oi_norm * 0.30) + (vol_norm * 0.25) + (fut_norm * 0.25) + (br_norm * 0.20)
        prob_ce = float(np.clip(50.0 + raw_bias * 50.0, 0.0, 100.0))
        prob_pe = float(np.clip(50.0 - raw_bias * 50.0, 0.0, 100.0))

        if near_call:
            prob_ce = max(0.0, prob_ce - 20.0)
        if near_put:
            prob_pe = max(0.0, prob_pe - 20.0)

        return prob_ce, prob_pe

    def evaluate_bar_data(self, df_5m, df_3m, df_15m, df_1h, df_4h, df_d, df_fut, df_vix, stock_changes, oc_data, is_pre_alert: bool = False):
        if not is_pre_alert:
            self.bar_index += 1
        bar_ts = df_5m.index[-1]
        self._cur_vix_df = df_vix
        if not is_pre_alert:
            self._fb_now = 0

        t5 = self.eval_timeframe(df_5m, is_5m=True)
        t3 = self.eval_timeframe(df_3m)
        t15 = self.eval_timeframe(df_15m)
        t1h = self.eval_timeframe(df_1h)
        t4h = self.eval_timeframe(df_4h)

        close = t5["close"]
        high = df_5m["high"].iloc[-1]
        low = df_5m["low"].iloc[-1]
        open_p = df_5m["open"].iloc[-1]
        atr10 = calc_atr(df_5m, 10).iloc[-1]
        vol = df_5m["volume"].iloc[-1]
        volAvg = calc_sma(df_5m["volume"], 20).iloc[-1]
        volOk = (not np.isnan(vol)) and vol > 0 and (not np.isnan(volAvg)) and volAvg > 0

        if not is_pre_alert and self.posSt != 0:
            self.tkLo = min(self.tkLo, low)
            self.tkHi = max(self.tkHi, high)

        inWin = in_session(bar_ts, PARAMS["sess_start"], PARAMS["sess_end"])
        techSide = t5["side"] if inWin else 0

        mtfAgree = (techSide != 0) and (t3["side"] == techSide) and (not PARAMS["mtf15Req"] or t15["side"] == techSide)
        techF = (techSide if mtfAgree else 0) if PARAMS["mtfOn"] else techSide
        mDir = techF
        if not is_pre_alert and (self.dirSince is None or mDir != self._prevDir):
            self._prevDir = mDir
            self.dirSince = bar_ts
            self.dirSinceBar = self.bar_index
        plusN = 0 if techSide == 0 else (
            (1 if t1h["side"] == techSide else 0) +
            (1 if t4h["side"] == techSide else 0) +
            (1 if (not PARAMS["mtf15Req"] and t15["side"] == techSide) else 0)
        )
        plusTxt = "+++" if plusN >= 3 else ("++" if plusN == 2 else ("+" if plusN == 1 else ""))

        diCE5 = (not np.isnan(t5["adx"])) and t5["adx"] > PARAMS["adxTrd"] and t5["diPl"] > PARAMS["diStrong"] and t5["diMi"] < PARAMS["diWeak"]
        diPE5 = (not np.isnan(t5["adx"])) and t5["adx"] > PARAMS["adxTrd"] and t5["diMi"] > PARAMS["diStrong"] and t5["diPl"] < PARAMS["diWeak"]
        diCEA = (not np.isnan(t3["adx"])) and t3["adx"] > PARAMS["adxTrd"] and t3["diPl"] > PARAMS["diStrong"] and t3["diMi"] < PARAMS["diWeak"]
        diPEA = (not np.isnan(t3["adx"])) and t3["adx"] > PARAMS["adxTrd"] and t3["diMi"] > PARAMS["diStrong"] and t3["diPl"] < PARAMS["diWeak"]
        diCEB = (not np.isnan(t15["adx"])) and t15["adx"] > PARAMS["adxTrd"] and t15["diPl"] > PARAMS["diStrong"] and t15["diMi"] < PARAMS["diWeak"]
        diPEB = (not np.isnan(t15["adx"])) and t15["adx"] > PARAMS["adxTrd"] and t15["diMi"] > PARAMS["diStrong"] and t15["diPl"] < PARAMS["diWeak"]

        diOkCE = (not PARAMS["diOn"]) or (((1 if diCE5 else 0) + (1 if diCEA else 0) + (1 if diCEB else 0)) >= PARAMS["diNeed"] if PARAMS["diMtf"] else diCE5)
        diOkPE = (not PARAMS["diOn"]) or (((1 if diPE5 else 0) + (1 if diPEA else 0) + (1 if diPEB else 0)) >= PARAMS["diNeed"] if PARAMS["diMtf"] else diPE5)
        adxOk = (not PARAMS["adxOn"]) or np.isnan(t5["adx"]) or t5["adx"] >= PARAMS["adxMin"]

        sma20_d = calc_sma(df_d["close"], PARAMS["dgLen"])
        d1, d2 = PARAMS["dgD1"], PARAMS["dgD2"]
        dgM1, dgM1p = sma20_d.iloc[-1 - d1], sma20_d.iloc[-2 - d1]
        dgM2, dgM2p = sma20_d.iloc[-1 - d2], sma20_d.iloc[-2 - d2]
        dgYL, dgYM, dgYH = df_d["low"].iloc[-2], sma20_d.iloc[-2], df_d["high"].iloc[-2]

        dgS1 = (dgM1 - dgM1p) / dgM1p * 100.0
        dgS2 = (dgM2 - dgM2p) / dgM2p * 100.0
        dgUp = dgS1 > PARAMS["dgFlat"] and dgS2 > PARAMS["dgFlat"]
        dgDn = dgS1 < -PARAMS["dgFlat"] and dgS2 < -PARAMS["dgFlat"]
        dgCE = (not PARAMS["dgOn"]) or (PARAMS["dgMode"] == "Sirf PE par") or dgUp
        dgPE = (not PARAMS["dgOn"]) or (PARAMS["dgMode"] == "Sirf CE par") or dgDn

        oiLook = PARAMS["oiLook"]
        futS = 0.0
        futTxt = "OFF" if not PARAMS["futOiOn"] else "N/A (OI data nahi)"
        if PARAMS["futOiOn"] and len(df_fut) > oiLook:
            pxCh = df_fut["close"].iloc[-1] - df_fut["close"].iloc[-1 - oiLook]
            oiCh = df_fut["oi"].iloc[-1] - df_fut["oi"].iloc[-1 - oiLook]
            if oiCh != 0:
                futS = 1.0 if (pxCh > 0 and oiCh > 0) else (0.5 if (pxCh > 0 and oiCh < 0) else (-1.0 if (pxCh < 0 and oiCh > 0) else (-0.5 if (pxCh < 0 and oiCh < 0) else 0.0)))
                futTxt = "Long Buildup (+1)" if futS == 1.0 else ("Short Covering (+0.5)" if futS == 0.5 else ("Short Buildup (-1)" if futS == -1.0 else "Long Unwinding (-0.5)"))

        atmNow = round(close / PARAMS["optStep"]) * PARAMS["optStep"]
        strikeCE = get_trade_strike(close, "CE")
        strikePE = get_trade_strike(close, "PE")
        selected_exp = oc_data.get("expiry", "") or (self.broker.get_selected_expiry() if not self.is_backtest else "BT_EXP")

        if self.ovCtr is None and atmNow > 0:
            self.ovCtr = atmNow

        oc_span = clamp_strike_span(PARAMS["ocN"])
        ov_span = clamp_strike_span(PARAMS["ovN"])

        ocOk = PARAMS["autoOc"] and oc_data.get("ocOk", False)
        volOk_pcr = PARAMS["ovOn"] and oc_data.get("volOk", False)
        ovUseF = volOk_pcr and PARAMS["ovFeed"]

        if ocOk:
            ocPcrVal = oc_data["ocPcr"]
        elif PARAMS["pcrIn"] > 0:
            ocPcrVal = PARAMS["pcrIn"]
        else:
            ocPcrVal = np.nan

        volPcrVal = oc_data["volPcr"] if volOk_pcr else np.nan
        pcrS = 0.0 if np.isnan(ocPcrVal) else (1.0 if ocPcrVal >= PARAMS["pcrBull"] else (-1.0 if ocPcrVal <= PARAMS["pcrBear"] else 0.0))
        volS = oc_data["volSig"] if ovUseF else 0.0
        oiScore = pcrS + futS + volS

        callEff = oc_data["ocCallK"] if (ocOk and not np.isnan(oc_data.get("ocCallK", np.nan))) else (
            oc_data["volCallK"] if (ovUseF and not np.isnan(oc_data.get("volCallK", np.nan))) else (
                PARAMS["callWall"] if PARAMS["callWall"] > 0 else np.nan
            )
        )
        putEff = oc_data["ocPutK"] if (ocOk and not np.isnan(oc_data.get("ocPutK", np.nan))) else (
            oc_data["volPutK"] if (ovUseF and not np.isnan(oc_data.get("volPutK", np.nan))) else (
                PARAMS["putWall"] if PARAMS["putWall"] > 0 else np.nan
            )
        )

        nearCall = (not np.isnan(callEff)) and (0.0 <= (callEff - close) / close * 100.0 <= PARAMS["wallBuf"])
        nearPut = (not np.isnan(putEff)) and (0.0 <= (close - putEff) / close * 100.0 <= PARAMS["wallBuf"])
        oiOkCE = (not nearCall) and (oiScore > -1)
        oiOkPE = (not nearPut) and (oiScore < 1)

        br = self.eval_breadth_and_sectors(stock_changes)
        score = br["score"]
        hasBr = not np.isnan(score)

        probCE, probPE = self.calc_oi_and_vol_probability(ocPcrVal, volPcrVal, futS, nearCall, nearPut, score)

        if not inWin:
            fin = "OFF TIME"
        elif mDir == 1:
            if not oiOkCE: fin = "SKIP (OI against CE)"
            elif not hasBr: fin = "CE BUY (breadth data nahi)"
            elif br["bullHi"] and oiScore >= 0: fin = "CE BUY - HIGH PROB"
            elif score >= 55: fin = "CE BUY - medium"
            else: fin = "SKIP (breadth weak)"
        elif mDir == -1:
            if not oiOkPE: fin = "SKIP (OI against PE)"
            elif not hasBr: fin = "PE BUY (breadth data nahi)"
            elif br["bearHi"] and oiScore <= 0: fin = "PE BUY - HIGH PROB"
            elif score <= 45: fin = "PE BUY - medium"
            else: fin = "SKIP (breadth weak)"
        else:
            fin = "WAIT"

        if PARAMS["requireHighProbOnly"]:
            sigCE = (fin == "CE BUY - HIGH PROB")
            sigPE = (fin == "PE BUY - HIGH PROB")
        else:
            sigCE = fin.startswith("CE BUY")
            sigPE = fin.startswith("PE BUY")

        probOkCE = (not PARAMS["oiProbFilterOn"]) or (probCE >= PARAMS["minOiProbCE"])
        probOkPE = (not PARAMS["oiProbFilterOn"]) or (probPE >= PARAMS["minOiProbPE"])

        rng5 = high - low
        cpos = ((close - low) / rng5) if rng5 > 0 else 0.5
        tmBlkR = (in_session(bar_ts, *PARAMS["tmS1"]) or in_session(bar_ts, *PARAMS["tmS2"]) or in_session(bar_ts, *PARAMS["tmS3"]))
        exBlkR = (bar_ts.weekday() == DOW_MAP[PARAMS["exDay"]])

        rawLateCE = (not np.isnan(t5["adx"])) and hasBr and t5["adx"] >= PARAMS["lateAdx"] and score >= PARAMS["lateBr"]
        rawLatePE = (not np.isnan(t5["adx"])) and hasBr and t5["adx"] >= PARAMS["lateAdx"] and score <= (100.0 - PARAMS["lateBr"])
        rawAr = np.isnan(t5["adx"]) or np.isnan(t5["adxPrev"]) or (t5["adx"] > t5["adxPrev"])
        rawRsiCE = np.isnan(t5["rsi"]) or t5["rsi"] <= PARAMS["rsiHi"]
        rawRsiPE = np.isnan(t5["rsi"]) or t5["rsi"] >= PARAMS["rsiLo"]
        rawCdCE = cpos >= PARAMS["cdPos"]
        rawCdPE = cpos <= (1.0 - PARAMS["cdPos"])
        rawVol = (not volOk) or (vol >= volAvg * PARAMS["vfMult"])

        pdhNear = (0 <= (dgYH - close) / close * 100.0 <= PARAMS["lvlBuf"])
        pdlNear = (0 <= (close - dgYL) / close * 100.0 <= PARAMS["lvlBuf"])
        rdUpNear = (math.ceil(close / PARAMS["rdStep"]) * PARAMS["rdStep"] - close) <= PARAMS["rdPts"]
        rdDnNear = (close - math.floor(close / PARAMS["rdStep"]) * PARAMS["rdStep"]) <= PARAMS["rdPts"]

        today_open = df_5m[df_5m.index.date == bar_ts.date()]["open"].iloc[0]
        rawOpCE = close > today_open

        vxLook = PARAMS["vxLook"]
        vix_now = df_vix["close"].iloc[-1] if not df_vix.empty else np.nan
        vix_prev = df_vix["close"].iloc[-1 - vxLook] if len(df_vix) > vxLook else np.nan
        rawVxCE = np.isnan(vix_now) or np.isnan(vix_prev) or vix_now <= vix_prev
        rawVxPE = np.isnan(vix_now) or np.isnan(vix_prev) or vix_now >= vix_prev

        v22CE = (not PARAMS["lateOn"] or not rawLateCE) and (not PARAMS["arOn"] or rawAr) and (not PARAMS["rsiOn"] or rawRsiCE) and (not PARAMS["cdOn"] or rawCdCE) and (not PARAMS["vfOn"] or rawVol) and not ((PARAMS["lvlOn"] and pdhNear) or (PARAMS["rdOn"] and rdUpNear)) and (not PARAMS["opOn"] or rawOpCE) and (not PARAMS["vxOn"] or rawVxCE) and not (PARAMS["tmOn"] and tmBlkR) and not (PARAMS["exOn"] and exBlkR)
        v22PE = (not PARAMS["lateOn"] or not rawLatePE) and (not PARAMS["arOn"] or rawAr) and (not PARAMS["rsiOn"] or rawRsiPE) and (not PARAMS["cdOn"] or rawCdPE) and (not PARAMS["vfOn"] or rawVol) and not ((PARAMS["lvlOn"] and pdlNear) or (PARAMS["rdOn"] and rdDnNear)) and (not PARAMS["vxOn"] or rawVxPE) and not (PARAMS["tmOn"] and tmBlkR) and not (PARAMS["exOn"] and exBlkR)

        gdCE = (0 if rawLateCE else 1) + (1 if rawAr else 0) + (1 if rawRsiCE else 0) + (1 if rawCdCE else 0) + (1 if rawVol else 0) + (0 if (pdhNear or rdUpNear) else 1) + (1 if rawOpCE else 0) + (1 if rawVxCE else 0) + (0 if tmBlkR else 1)
        gdPE = (0 if rawLatePE else 1) + (1 if rawAr else 0) + (1 if rawRsiPE else 0) + (1 if rawCdPE else 0) + (1 if rawVol else 0) + (0 if (pdlNear or rdDnNear) else 1) + (1 if (not PARAMS["peBelowOpen"] or close < today_open) else 0) + (1 if rawVxPE else 0) + (0 if tmBlkR else 1)
        grade_str = f"CE:{'A' if gdCE>=PARAMS['gdA'] else ('B' if gdCE>=PARAMS['gdB'] else 'C')}({gdCE}/9) | PE:{'A' if gdPE>=PARAMS['gdA'] else ('B' if gdPE>=PARAMS['gdB'] else 'C')}({gdPE}/9)"

        coolOk = (self.bar_index - self.lastExit) >= PARAMS["coolBars"]
        stCE = t5["sdir"] < 0
        stPE = t5["sdir"] > 0
        extOk = abs(close - t5["ema21"]) <= atr10 * PARAMS["extMult"]

        peHtfOk = (PARAMS["peHtf"] == "OFF") or (t1h["side"] == -1 if PARAMS["peHtf"] == "1h PE" else (t1h["side"] == -1 and t4h["side"] == -1))
        peOk = (not hasBr or score <= PARAMS["peBrMax"]) and (np.isnan(t5["adx"]) or t5["adx"] >= PARAMS["peAdxMin"]) and peHtfOk and (not PARAMS["peBelowOpen"] or close < today_open)
        peScore = (1 if dgDn else 0) + (1 if close < dgYM else 0) + (1 if close < dgYL else 0) + (1 if (t1h["side"] == -1 and t4h["side"] == -1) else 0) + (1 if oiScore < 0 else 0)
        peScOk = (PARAMS["peScMin"] == 0) or (peScore >= PARAMS["peScMin"])

        is_idle = (self.posSt == 0) and (self.wSt == 0 if (self.is_backtest and self.bt_entry_mode == "REAL_BLUE_ONLY") else True)
        entCE = is_idle and sigCE and probOkCE and self.armCE and coolOk and extOk and stCE and adxOk and PARAMS["allowCE"] and diOkCE and dgCE and br["scCE"] and v22CE
        entPE = is_idle and sigPE and probOkPE and self.armPE and coolOk and extOk and stPE and adxOk and PARAMS["allowPE"] and peOk and diOkPE and dgPE and peScOk and br["scPE"] and v22PE

        if is_pre_alert:
            if (entCE or entPE) and self.last_pre_alert_bar != self.bar_index:
                self.last_pre_alert_bar = self.bar_index
                side_p = "CE" if entCE else "PE"
                strk_p = strikeCE if entCE else strikePE
                p_val = probCE if entCE else probPE
                self.alert(f"PRE-ALERT: {side_p} ({int(strk_p)} {PARAMS['strikeMode']} | Exp: {selected_exp}) ban raha hai @ {close:.1f} (Prob: {p_val:.0f}%)")
            self._dash_pre(entCE, entPE)
            return

        sgn = -1 if self.posSt == -1 else 1
        exit_mode = PARAMS["exitMode"].upper()
        if PARAMS["trOn"] and exit_mode == "T1":
            exit_mode = "T2"

        chk_high = high if PARAMS["useHighLowForTarget"] else close
        chk_low = low if PARAMS["useHighLowForTarget"] else close

        slHit = self.posSt != 0 and (close <= self.posSl if sgn == 1 else close >= self.posSl)
        t1Touch = self.posSt != 0 and (chk_high >= self.posT1 if sgn == 1 else chk_low <= self.posT1)
        t2Touch = self.posSt != 0 and (chk_high >= self.posT2 if sgn == 1 else chk_low <= self.posT2)
        trendBad = self.posSt != 0 and ((t5["sdir"] > 0) if self.posSt == 1 else (t5["sdir"] < 0))

        if self.posSt != 0 and exit_mode == "T1_T2" and t1Touch and not self.t1Booked:
            pct = PARAMS["t1ExitPct"] / 100.0
            lots_to_book = max(1, int(round(self.activeLots * pct))) if self.activeLots > 1 else 1
            booked_ratio = (lots_to_book / self.activeLots) if self.activeLots > 0 else pct
            t1_px = self.posT1 if PARAMS["useHighLowForTarget"] else close
            self.realizedTradePnl += sgn * (t1_px - self.posEn) * booked_ratio
            self.remainingLots = max(0, self.activeLots - lots_to_book)
            self._bt_partials.append(dict(ts=bar_ts, spot=t1_px, lots=lots_to_book))
            self.t1Booked = True
            self.posSl = self.posEn
            self.posMv = True
            side_str = "CE" if self.posSt == 1 else "PE"
            self.broker.paper_reason = "T1_PARTIAL"
            self._order(side_str, self.activeStrike, lots_to_book, action="SELL", expiry_date=self.activeExpiry)
            self.alert(f"T1 PARTIAL BOOKED ({PARAMS['t1ExitPct']}%) @ {t1_px:.1f} | Remaining trailing to T2 ({self.posT2:.1f}), SL at Entry ({self.posSl:.1f})")
            if self.remainingLots == 0:
                self._record_closed_trade(bar_ts, t1_px, "T1_FULL", self.realizedTradePnl)
                self.posSt = 0
                self.posMv = False
                self.t1Booked = False
                self.realizedTradePnl = 0.0
                self.lastExit = self.bar_index

        target_exit_triggered = False
        target_exit_px = close
        target_exit_label = ""

        if self.posSt != 0:
            if exit_mode == "T1" and t1Touch:
                target_exit_triggered = True
                target_exit_px = self.posT1 if PARAMS["useHighLowForTarget"] else close
                target_exit_label = "T1"
            elif exit_mode in ("T2", "T1_T2") and t2Touch:
                target_exit_triggered = True
                target_exit_px = self.posT2 if PARAMS["useHighLowForTarget"] else close
                target_exit_label = "T2"

        if self.posSt != 0 and not target_exit_triggered and not slHit:
            candBE = (self.posEn + sgn * PARAMS["beLock"] * self.posR) if (PARAMS["beOn"] and ((close >= self.posEn + PARAMS["beR"] * self.posR) if sgn == 1 else (close <= self.posEn - PARAMS["beR"] * self.posR))) else np.nan
            candT1 = (self.posEn + sgn * self.posR) if (exit_mode == "T2" and t1Touch) else np.nan
            if sgn == 1:
                newSl = max(self.posSl, np.nanmax([self.posSl, candBE, candT1]))
                if newSl > self.posSl:
                    self.posSl = newSl
                    self.posMv = True
            else:
                newSl = min(self.posSl, np.nanmin([self.posSl, candBE, candT1]))
                if newSl < self.posSl:
                    self.posSl = newSl
                    self.posMv = True

        exitNow = self.posSt != 0 and (slHit or target_exit_triggered or trendBad or not inWin)
        if exitNow:
            if target_exit_triggered:
                exRes = target_exit_label
                exPx = target_exit_px
            elif slHit:
                exRes = "TSL" if self.posMv else "SL"
                exPx = close
            elif trendBad:
                exRes = "Trend"
                exPx = close
            else:
                exRes = "Time"
                exPx = close

            rem_ratio = (self.remainingLots / self.activeLots) if self.activeLots > 0 else 1.0
            total_trade_pnl = self.realizedTradePnl + sgn * (exPx - self.posEn) * rem_ratio
            side_str = "CE" if self.posSt == 1 else "PE"

            self.broker.paper_reason = exRes
            if self.remainingLots > 0:
                self._order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)

            self._record_closed_trade(bar_ts, exPx, exRes, total_trade_pnl)
            self.posSt = 0
            self.posMv = False
            self.t1Booked = False
            self.remainingLots = 0
            self.realizedTradePnl = 0.0
            self.lastExit = self.bar_index

        if not inWin: why = "Window band"
        elif self.posSt != 0: why = f"Trade chal rahi (ExitMode: {exit_mode})"
        elif techSide == 0: why = f"Tech {max(t5['bull'], t5['bear'])}/{t5['maxC']} need {t5['needE']}"
        elif mDir == 0: why = "3m/15m agree nahi" if (techSide != 0 and techF == 0) else "Trend ulta"
        elif not (sigCE or sigPE): why = fin
        elif (sigCE and not probOkCE): why = f"OI+Vol Prob {probCE:.0f}% < {PARAMS['minOiProbCE']:.0f}%"
        elif (sigPE and not probOkPE): why = f"OI+Vol Prob {probPE:.0f}% < {PARAMS['minOiProbPE']:.0f}%"
        elif not extOk: why = "Price EMA se door"
        elif (sigCE and not stCE) or (sigPE and not stPE): why = "Supertrend ulta"
        elif not coolOk: why = "Cooldown"
        elif (sigCE and not self.armCE) or (sigPE and not self.armPE): why = "Signal use ho chuka"
        elif (sigCE or sigPE) and not adxOk: why = f"Sideways ADX {t5['adx']:.0f} < {PARAMS['adxMin']:.0f}"
        elif (sigCE and not diOkCE) or (sigPE and not diOkPE): why = f"DI/ADX filter ({PARAMS['diNeed']} of 3 TF)"
        elif (sigCE and not dgCE) or (sigPE and not dgPE): why = f"Daily gate 7d:{dgS1:+.2f}% 5d:{dgS2:+.2f}%"
        elif sigPE and dgPE and not peScOk: why = f"PE score {peScore}/5 (need {PARAMS['peScMin']})"
        elif (sigCE and not br["scCE"]) or (sigPE and not br["scPE"]): why = "Sector signal ke khilaf"
        elif not v22CE or not v22PE: why = "v22 filter block"
        else: why = "Signal OK"

        slD = atr10 * PARAMS["slMult"]
        riskRs = PARAMS["capital"] * PARAMS["riskPct"] / 100.0
        lotRisk = slD * PARAMS["optDelta"] * PARAMS["optLot"]
        lots = max(1, int(math.floor(riskRs / lotRisk))) if lotRisk > 0 else 1

        fb_msg = "-- | " + self.wLast
        if entCE or entPE:
            lvS = 1 if entCE else -1
            side_lbl = "CE" if entCE else "PE"
            arrow_icon = "[GREEN ARROW]" if entCE else "[RED ARROW]"
            ent_prob = probCE if entCE else probPE
            chosen_strike = strikeCE if entCE else strikePE
            init_sl = close - lvS * slD
            self.events.append(dict(t=bar_ts, k="BUY CE" if entCE else "BUY PE", text=side_lbl + plusTxt, p=plusN))
            self.lastSigT, self.lastSigTx, self.lastSigBar = bar_ts, side_lbl + plusTxt, self.bar_index

            if not (self.is_backtest and self.bt_entry_mode == "REAL_BLUE_ONLY"):
                self.posSt = lvS
                self.posEn = close
                self.posSl = init_sl
                self.posT1 = close + lvS * slD * PARAMS["rrT"]
                self.posT2 = close + lvS * slD * (PARAMS["rrT"] + 1.0)
                self.posR = slD
                self.tkLo = low
                self.tkHi = high
                self.t1Booked = False
                self.realizedTradePnl = 0.0
                self.activeStrike = chosen_strike
                self.activeExpiry = selected_exp
                self.activeLots = lots
                self.remainingLots = lots

                self.entTx = side_lbl + plusTxt
                self.entT = bar_ts
                self.entAdx = t5["adx"]
                self.entSc = score
                self.entProbCE = probCE
                self.entProbPE = probPE

            if PARAMS["wfOn"]:
                self.wSt = lvS
                self.wNsig += 1
                self.wBar = self.bar_index
                self.wSigC = close
                self.wSl = init_sl
                self.wExt = close
                self.wCloses = [close]
                self.fbEn = np.nan
                self.wPendingSide = side_lbl
                self.wPendingStrike = chosen_strike
                self.wPendingExpiry = selected_exp
                self.wPendingLots = lots
                self.wPendingPlus = plusTxt
                self.wPendingAdx = t5["adx"]
                self.wPendingSc = score
                self.wPendingProbCE = probCE
                self.wPendingProbPE = probPE
                fb_msg = f"WATCH {side_lbl} STARTED (Waiting for Blue Arrow)"
            else:
                order_ok = self._order(side_lbl, chosen_strike, lots, action="BUY", expiry_date=selected_exp)
                self._log_real_trade_entry(bar_ts, side_lbl, chosen_strike, selected_exp, lots, close, ent_prob, order_ok)

            self.alert(
                f"{arrow_icon} STEP 1: INITIAL {side_lbl} SIGNAL ({fin}) @ {close:.1f} | Prob: {ent_prob:.0f}%\n"
                f"Strike: {int(chosen_strike)} {side_lbl} ({PARAMS['strikeMode']}) | Expiry: {selected_exp} ({PARAMS['expiryMode']})\n"
                f"WATCH MODE ON - Final Buy (Blue Arrow) ki calculation chal rahi hai...\n"
                f"Exit Mode: {exit_mode} | SL: {init_sl:.1f} | T1: {close + lvS * slD * PARAMS['rrT']:.1f} | T2: {close + lvS * slD * (PARAMS['rrT'] + 1.0):.1f}"
            )

        elif PARAMS["wfOn"] and self.wSt != 0:
            self.wExt = min(self.wExt, low) if self.wSt == 1 else max(self.wExt, high)
            self.wCloses.append(close)

            wTouch = ((low <= self.wSl if PARAMS["wfWick"] else close <= self.wSl) if self.wSt == 1
                      else (high >= self.wSl if PARAMS["wfWick"] else close >= self.wSl))
            wGone = (self.posSt == 0) and not (self.is_backtest and self.bt_entry_mode == "REAL_BLUE_ONLY")
            wExp = (self.bar_index - self.wBar) > max(PARAMS["wfMax"], PARAMS["wfMin"])

            if wTouch or wGone or wExp:
                reason = "Dip ne SL touch kiya" if wTouch else ("Trade pehle khatam" if wGone else "Time out (20 bars)")
                self.wLast = f"Nahi: {reason}"
                self.wNcan += 1
                self.wSt = 0
                fb_msg = "-- | " + self.wLast
                self.alert(f"[WATCH CANCELLED] ({reason}) - Final Buy Blue Arrow nahi bana.")
            else:
                rule = PARAMS["wfRule"]
                wCrvC = (self.wSigC - self.wExt >= PARAMS["wfDip"] * atr10) and (high > low) and (close > open_p or (min(open_p, close) - low) >= PARAMS["wfWk"] / 100.0 * (high - low))
                wCrvP = (self.wExt - self.wSigC >= PARAMS["wfDip"] * atr10) and (high > low) and (close < open_p or (high - max(open_p, close)) >= PARAMS["wfWk"] / 100.0 * (high - low))
                wCrvEC = (self.wExt < self.wSigC) and (close > open_p) and (close > self.wCloses[-2])
                wCrvEP = (self.wExt > self.wSigC) and (close < open_p) and (close < self.wCloses[-2])

                wUpTh = PARAMS["wfUpPts"] if PARAMS["wfUpPts"] > 0 else PARAMS["wfUp"] * atr10
                wUpC = (wUpTh > 0) and (self.bar_index - self.wBar >= 2) and (close > open_p) and (close >= self.wSigC + wUpTh)
                wUpP = (wUpTh > 0) and (self.bar_index - self.wBar >= 2) and (close < open_p) and (close <= self.wSigC - wUpTh)

                smaF = pd.Series(self.wCloses).rolling(PARAMS["wfF"]).mean().iloc[-1] if len(self.wCloses) >= PARAMS["wfF"] else np.mean(self.wCloses)
                smaS = pd.Series(self.wCloses).rolling(PARAMS["wfS"]).mean().iloc[-1] if len(self.wCloses) >= PARAMS["wfS"] else np.mean(self.wCloses)

                if self.wSt == 1:
                    raw_ok = (wCrvEC or wUpC) if rule == "E" else (smaF > smaS if rule == "D" else (wCrvC if rule == "C" else (close >= self.wExt + PARAMS["wfA"] * atr10 if rule == "A" else close > self.wSigC)))
                else:
                    raw_ok = (wCrvEP or wUpP) if rule == "E" else (smaF < smaS if rule == "D" else (wCrvP if rule == "C" else (close <= self.wExt - PARAMS["wfA"] * atr10 if rule == "A" else close < self.wSigC)))

                if raw_ok and (self.bar_index - self.wBar >= PARAMS["wfMin"]):
                    fb_side = "CE" if self.wSt == 1 else "PE"
                    lvS = self.wSt
                    pts = lvS * (close - self.wSigC)
                    ent_prob = self.wPendingProbCE if lvS == 1 else self.wPendingProbPE
                    self.wLast = "FINAL BUY"
                    self.fbEn = close
                    self.wNfin += 1
                    self._fb_now = lvS
                    self.events.append(dict(t=bar_ts, k="FINAL BUY " + fb_side, text=f"{pts:+.0f}p"))
                    fb_msg = f">>> FINAL BUY {fb_side} ({pts:+.1f}p | Prob:{ent_prob:.0f}%) <<<"

                    if self.is_backtest and self.bt_entry_mode == "REAL_BLUE_ONLY":
                        self.posSt = lvS
                        self.posEn = close
                        self.posSl = close - lvS * slD
                        self.posT1 = close + lvS * slD * PARAMS["rrT"]
                        self.posT2 = close + lvS * slD * (PARAMS["rrT"] + 1.0)
                        self.posR = slD
                        self.tkLo = low
                        self.tkHi = high
                        self.t1Booked = False
                        self.realizedTradePnl = 0.0
                        self.activeStrike = self.wPendingStrike
                        self.activeExpiry = self.wPendingExpiry
                        self.activeLots = self.wPendingLots
                        self.remainingLots = self.wPendingLots
                        self.entTx = f"FB_{fb_side}{self.wPendingPlus}"
                        self.entT = bar_ts
                        self.entAdx = self.wPendingAdx
                        self.entSc = self.wPendingSc
                        self.entProbCE = self.wPendingProbCE
                        self.entProbPE = self.wPendingProbPE

                    order_ok = self._order(fb_side, self.activeStrike, self.activeLots, action="BUY", expiry_date=self.activeExpiry)
                    self._log_real_trade_entry(bar_ts, fb_side, self.activeStrike, self.activeExpiry, self.activeLots, close, ent_prob, order_ok)

                    self.alert(
                        f"[BLUE ARROW] STEP 2: FINAL BUY {fb_side} CONFIRMED @ {close:.1f} ({pts:+.1f}p) | Prob: {ent_prob:.0f}%\n"
                        f"REAL TRADE #{self.real_trade_count} | NIFTY [{self.activeExpiry}] {int(self.activeStrike)} {fb_side} ({PARAMS['strikeMode']}) | Lots: {self.activeLots}\n"
                        f"Broker Order Sent: {order_ok} | Exit Mode: {exit_mode} | SL: {self.posSl:.1f} | T1: {self.posT1:.1f} | T2: {self.posT2:.1f}"
                    )
                    self.wSt = 0
                else:
                    fb_msg = f"WATCH {'CE' if self.wSt==1 else 'PE'} bar {self.bar_index - self.wBar}/{PARAMS['wfMax']} dip {abs(self.wSigC - self.wExt):.0f}"

        self.armCE = (self.armCE and not entCE) if sigCE else True
        self.armPE = (self.armPE and not entPE) if sigPE else True

        self._dash_capture(locals())

        if not self.is_backtest:
            s_txt = lambda x: "CE" if x == 1 else ("PE" if x == -1 else "-")
            print("=" * 82)
            print(f"NIFTY OPT PRO v28 (5m) | {bar_ts.strftime('%Y-%m-%d %H:%M IST')} | LTP: {close:.2f}")
            print(f"REAL TRADES TAKEN: {self.real_trade_count} (Live Broker Orders: {self.real_live_orders_sent}) | Strike: {PARAMS['strikeMode']} | Exp: {selected_exp} | Exit: {exit_mode}")
            print(f"MTF 3m/5m/15m: {s_txt(t3['side'])} / {s_txt(t5['side'])} / {s_txt(t15['side'])} | 1h/4h: {s_txt(t1h['side'])} / {s_txt(t4h['side'])}")
            print(f"Signal: {fin} {plusTxt} | Breadth: {score:.0f} ({br['brTxt']}) | Grade: {grade_str}")
            print(f"OI+VOL PROBABILITY: CE {probCE:.0f}% | PE {probPE:.0f}% (Filter: {'ON' if PARAMS['oiProbFilterOn'] else 'OFF'})")
            print(f"Option OI (+-{oc_span} strk): {ocPcrVal:.2f} (S:{putEff:.0f} R:{callEff:.0f}) | VOL PCR (+-{ov_span} strk): {volPcrVal:.2f} | Fut OI: {futTxt}")
            print(f"WATCH / FINAL: {fb_msg}")
            if self.posSt != 0:
                print(f"ACTIVE POSITION: {int(self.activeStrike)} {'CE' if self.posSt==1 else 'PE'} [{self.activeExpiry}] | Entry: {self.posEn:.1f} | SL: {self.posSl:.1f} | T1: {self.posT1:.1f} | T2: {self.posT2:.1f} | RemLots: {self.remainingLots}/{self.activeLots}")
            print(f"ADX(14): {t5['adx']:.1f} (D+:{t5['diPl']:.0f} D-:{t5['diMi']:.0f}) | OR: {t5['orTxt']} | Kyu nahi?: {why}")
            print(f"Lots: {lots} | Session Log W/L: {self.winN}/{self.lossN} ({self.totPnl:+.1f}p)")
            print("=" * 82)

    def process_live_bar(self, is_pre_alert: bool = False):
        now_ist = dt.datetime.now(IST)
        main_sym = CONFIG["CHART_SYMBOL"]

        df_5m = self.broker.get_candles(main_sym, interval="5", days=7)
        if df_5m.empty or len(df_5m) < 60:
            return
        if not is_pre_alert and df_5m.index[-1] > now_ist - dt.timedelta(minutes=5):
            df_5m = df_5m.iloc[:-1]

        df_3m = self.broker.get_candles(main_sym, interval="3", days=5)
        df_15m = self.broker.get_candles(main_sym, interval="15", days=10)
        df_1h = self.broker.get_candles(main_sym, interval="60", days=20)
        df_4h = self.broker.get_candles(main_sym, interval="240", days=45)
        df_d = self.broker.get_candles(main_sym, interval="D", days=60)
        df_fut = self.broker.get_candles("NIFTY_FUT", interval="5", days=3)
        df_vix = self.broker.get_candles("INDIAVIX", interval="5", days=3)

        close = df_5m["close"].iloc[-1]
        self.broker.last_spot = float(close)  # paper trading ke liye latest spot
        atmNow = round(close / PARAMS["optStep"]) * PARAMS["optStep"]
        if self.ovCtr is None and atmNow > 0:
            self.ovCtr = atmNow

        oc_data = self.broker.get_option_chain_metrics(
            atmNow, self.ovCtr, PARAMS["ocN"], PARAMS["ovN"]
        ) if (PARAMS["autoOc"] or PARAMS["ovOn"]) else {}

        stock_changes = self.broker.get_breadth_changes()
        self.evaluate_bar_data(df_5m, df_3m, df_15m, df_1h, df_4h, df_d, df_fut, df_vix, stock_changes, oc_data, is_pre_alert=is_pre_alert)
        self.render_dashboard()


# ==============================================================================
# 6. HISTORICAL BACKTEST RUNNER
# ==============================================================================
def run_backtest(broker: BrokerConnector, days: int = 30):
    bt_type = CONFIG.get("BACKTEST_ENTRY_TYPE", "BOTH").upper()
    print(f"\nFetching Historical Data ({days} days) for Backtest | Strike: {PARAMS['strikeMode']} | Expiry: {PARAMS['expiryMode']} | Exit: {PARAMS['exitMode']}...")
    main_sym = CONFIG["CHART_SYMBOL"]

    df_5m = broker.get_candles(main_sym, interval="5", days=days + 10)
    df_3m = broker.get_candles(main_sym, interval="3", days=days + 10)
    df_15m = broker.get_candles(main_sym, interval="15", days=days + 15)
    df_1h = broker.get_candles(main_sym, interval="60", days=days + 25)
    df_4h = broker.get_candles(main_sym, interval="240", days=days + 50)
    df_d = broker.get_candles(main_sym, interval="D", days=days + 60)
    df_fut = broker.get_candles("NIFTY_FUT", interval="5", days=days + 10)
    df_vix = broker.get_candles("INDIAVIX", interval="5", days=days + 10)

    if df_5m.empty or len(df_5m) < 100:
        msg = f"Backtest ke liye paryapt historical data nahi mila (5m bars: {len(df_5m)}, 3m: {len(df_3m)}, 15m: {len(df_15m)}, 1h: {len(df_1h)}, 4h: {len(df_4h)}, D: {len(df_d)})."
        if getattr(broker, "last_error", ""):
            msg += f" | Broker error: {broker.last_error}"
        print(msg)
        return {"error": msg, "counts": {"5m": len(df_5m), "3m": len(df_3m), "15m": len(df_15m), "1h": len(df_1h), "4h": len(df_4h), "D": len(df_d)}}

    stock_daily = {}
    for sym, _ in BREADTH_STOCKS:
        d_s = broker.get_candles(sym, interval="D", days=days + 15)
        if not d_s.empty:
            d_s["pct"] = d_s["close"].pct_change() * 100.0
            stock_daily[sym] = d_s["pct"]

    modes_to_run = ["ALL_SIGNALS", "REAL_BLUE_ONLY"] if bt_type == "BOTH" else [bt_type]
    opt_provider = OptionPriceProvider(broker)  # dono modes ke liye same cache (API calls kam)

    for mode_label in modes_to_run:
        engine = NiftyOptionProEngine(broker, is_backtest=True, bt_entry_mode=mode_label)
        engine.opt_provider = opt_provider
        oc_bt = {
            "expiry": PARAMS["expiryMode"],
            "ocOk": PARAMS["pcrIn"] > 0,
            "ocPcr": PARAMS["pcrIn"] if PARAMS["pcrIn"] > 0 else np.nan,
            "ocCallK": PARAMS["callWall"] if PARAMS["callWall"] > 0 else np.nan,
            "ocPutK": PARAMS["putWall"] if PARAMS["putWall"] > 0 else np.nan,
            "volOk": False,
            "volPcr": np.nan,
            "volSig": 0.0
        }

        for i in range(60, len(df_5m)):
            sub_5m = df_5m.iloc[:i + 1]
            cur_ts = sub_5m.index[-1]
            cur_date = cur_ts.date()

            sub_3m = df_3m[df_3m.index <= cur_ts]
            sub_15m = df_15m[df_15m.index <= cur_ts]
            sub_1h = df_1h[df_1h.index <= cur_ts]
            sub_4h = df_4h[df_4h.index <= cur_ts]
            sub_d = df_d[df_d.index.date <= cur_date]
            sub_fut = df_fut[df_fut.index <= cur_ts] if not df_fut.empty else pd.DataFrame()
            sub_vix = df_vix[df_vix.index <= cur_ts] if not df_vix.empty else pd.DataFrame()

            if len(sub_d) < 30 or len(sub_3m) < 30 or len(sub_15m) < 30 or len(sub_1h) < 30 or len(sub_4h) < 30:
                continue

            changes = {}
            for sym, _ in BREADTH_STOCKS:
                s_pct = stock_daily.get(sym)
                if s_pct is not None:
                    valid = s_pct[s_pct.index.date <= cur_date]
                    changes[sym] = valid.iloc[-1] if not valid.empty else np.nan
                else:
                    changes[sym] = np.nan

            engine.evaluate_bar_data(sub_5m, sub_3m, sub_15m, sub_1h, sub_4h, sub_d, sub_fut, sub_vix, changes, oc_bt)

        csv_name = f"backtest_{mode_label}_{PARAMS['strikeMode']}_{PARAMS['exitMode']}.csv"
        if engine.trade_journal:
            j_df = pd.DataFrame(engine.trade_journal)
            j_df.to_csv(csv_name, index=False)
            try:
                _net = pd.to_numeric(j_df["NetPnL_Rs"], errors="coerce")
                print(f"[Backtest {mode_label}] {len(j_df)} trades | PnL {j_df['PnL_Pts'].sum():+.1f} pts | "
                      f"Net P&L Rs {_net.sum():+,.0f} ({int(_net.notna().sum())} trades me premium mila) | "
                      f"PremiumSrc: {j_df['PremiumSrc'].fillna('NA').value_counts().to_dict()}")
            except Exception:
                pass
        else:
            pd.DataFrame(columns=["EntryTime","ExitTime","Signal","Contract","Strike","Expiry","ExpiryDate","ExpiryDateSrc","Lots","Qty","EntryPremium","ExitPremium","PremiumSrc","GrossPnL_Rs","Fees_Rs","NetPnL_Rs","EntryPx","ExitPx","ExitReason","PnL_Pts","FB_PnL_Pts","OI_Prob%","MAE","MFE","ADX","Breadth"]).to_csv(csv_name, index=False)

        if CONFIG.get("DASH_ON", True):
            dash_path = f"dashboard_backtest_{mode_label}.html"
            engine.render_dashboard(dash_path)

    return {"ok": True, "modes": modes_to_run, "bars_5m": len(df_5m)}


# ==============================================================================
# 7. STREAMLIT DESKTOP WEB UI (FULL CONTROLS FOR EVERY PARAMETER & GATE)
# ==============================================================================
# ==============================================================================
# 7B. ALL SETTINGS PANEL (TradingView ke "Settings > Inputs" jaisa) + SAVE / LOAD
# ==============================================================================
_POS_CHOICES = ["Top Left", "Top Center", "Top Right", "Middle Left", "Middle Center", "Middle Right",
                "Bottom Left", "Bottom Center", "Bottom Right"]
# Jin settings ka sidebar me widget nahi tha (auto-detect fail ho to ye list use hoti hai)
_KNOWN_HIDDEN_PARAMS = ["chartType", "optStep", "optSym", "optEntry", "lateAdx", "lateBr", "arN", "cdPos", "lvlBuf",
                        "rdStep", "rdPts", "vxLook", "tmS1", "tmS2", "tmS3", "beR", "beLock", "gdA", "gdB",
                        "ovBull", "ovBear", "preSec", "implRef"]
_KNOWN_HIDDEN_DASH = ["showMk", "lblMode", "lblBars", "wfArrow", "wfMaShow", "posSig", "posLg", "posBr", "posOi",
                      "posLs", "scPos", "scPosA", "posJ", "posPh", "posXs", "gdPos", "vp_pos", "jPg", "vp_useSpot",
                      "ph1S", "ph2S", "phE"]


def _hidden_setting_keys():
    """(params_keys, dash_keys) jinka sidebar me koi widget nahi hai."""
    try:
        full = open(__file__, encoding="utf-8").read()
        start = full.rindex("def run_streamlit_desktop_app():")  # asli def (ye helper uske pehle hai)
        a = full.index("with st.sidebar:", start)
        b = full.index("Data Connection Test", a)
        ui = full[a:b]
        hp = [k for k in PARAMS if f'PARAMS["{k}"]' not in ui]
        hd = [k for k in DASH if f'DASH["{k}"]' not in ui]
        return hp, hd
    except Exception:
        return ([k for k in _KNOWN_HIDDEN_PARAMS if k in PARAMS], [k for k in _KNOWN_HIDDEN_DASH if k in DASH])


def _setting_widget(st, store: dict, k: str, key_prefix: str):
    v = store[k]
    wk = f"{key_prefix}_{k}"
    if isinstance(v, bool):
        store[k] = st.checkbox(k, value=v, key=wk)
    elif isinstance(v, int):
        store[k] = int(st.number_input(k, value=int(v), step=1, key=wk))
    elif isinstance(v, float):
        store[k] = float(st.number_input(k, value=float(v), key=wk))
    elif isinstance(v, (tuple, list)) and len(v) == 2:
        c1, c2 = st.columns(2)
        a = c1.text_input(f"{k} (from HH:MM)", value=str(v[0]), key=wk + "_a")
        b = c2.text_input(f"{k} (to HH:MM)", value=str(v[1]), key=wk + "_b")
        store[k] = (a.strip(), b.strip())
    elif k.lower().startswith("pos") or k.lower().endswith("pos") or k.lower().endswith("posa"):
        opts = _POS_CHOICES if v in _POS_CHOICES else [v] + _POS_CHOICES
        store[k] = st.selectbox(k, opts, index=opts.index(v), key=wk)
    else:
        store[k] = st.text_input(k, value=str(v), key=wk)


def apply_settings_dict(d: dict):
    """Saved settings JSON ko PARAMS / DASH me wapas lagata hai (type bachakar)."""
    n = 0
    for grp, tgt in (("PARAMS", PARAMS), ("DASH", DASH)):
        for k, v in (d.get(grp) or {}).items():
            if k not in tgt:
                continue
            old = tgt[k]
            try:
                if isinstance(old, bool):
                    v = bool(v)
                elif isinstance(old, int):
                    v = int(v)
                elif isinstance(old, float):
                    v = float(v)
                elif isinstance(old, tuple) and isinstance(v, (list, tuple)):
                    v = tuple(v)
            except Exception:
                continue
            tgt[k] = v
            n += 1
    return n


# ---- Persistent SAVE (ek click me settings file me save, agli baar app khulne par apne aap load) ----
SETTINGS_SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nifty_option_saved_settings.json")
# Sirf safe sidebar settings (API token/ID aur AUTO_PLACE_ORDER jaan-bujhkar save nahi hote)
_SAVE_CONFIG_KEYS = ["BROKER", "CHART_SYMBOL", "PAPER_TRADING", "PAPER_CAPITAL", "PAPER_BROKERAGE_PER_ORDER",
                     "PAPER_SLIPPAGE_PTS", "BACKTEST_DAYS", "BACKTEST_ENTRY_TYPE"]


def save_current_settings():
    data = {"PARAMS": PARAMS, "DASH": DASH, "CONFIG": {k: CONFIG[k] for k in _SAVE_CONFIG_KEYS if k in CONFIG}}
    with open(SETTINGS_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)
    return len(PARAMS) + len(DASH) + len(data["CONFIG"])


def load_saved_settings():
    """Saved file ho to PARAMS / DASH / CONFIG me lagata hai (file na ho to kuchh nahi badalta)."""
    if not os.path.exists(SETTINGS_SAVE_FILE):
        return 0
    try:
        with open(SETTINGS_SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        n = apply_settings_dict(d)
        for k, v in (d.get("CONFIG") or {}).items():
            if k in _SAVE_CONFIG_KEYS and k in CONFIG:
                try:
                    old = CONFIG[k]
                    CONFIG[k] = bool(v) if isinstance(old, bool) else int(v) if isinstance(old, int) else float(v) if isinstance(old, float) else v
                    n += 1
                except Exception:
                    pass
        return n
    except Exception:
        return 0


def render_all_settings_panel(st):
    """Sidebar ke end me: (1) jo settings pehle dikhti hi nahi thi, (2) saari settings ek jagah, (3) save / load."""
    hp, hd = _hidden_setting_keys()
    st.header("13. Baaki Saari Settings (TradingView jaisa)")
    st.caption(f"Ye {len(hp)} indicator settings aur {len(hd)} dashboard settings upar ke sections me nahi thi. "
               "Ab yahan se badal sakte ho.")
    with st.expander(f"13A. Extra Indicator Settings ({len(hp)})"):
        for k in hp:
            _setting_widget(st, PARAMS, k, "xp")
    with st.expander(f"13B. Extra Dashboard / Table Position Settings ({len(hd)})"):
        for k in hd:
            _setting_widget(st, DASH, k, "xd")
    with st.expander(f"13C. Saari Settings Ek Nazar Me ({len(PARAMS)} + {len(DASH)})"):
        rows = [{"Group": "Indicator", "Setting": k, "Value": str(v)} for k, v in PARAMS.items()]
        rows += [{"Group": "Dashboard", "Setting": k, "Value": str(v)} for k, v in DASH.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("13D. Settings Save / Load (JSON)"):
        st.download_button("Download Current Settings (JSON)",
                           json.dumps({"PARAMS": PARAMS, "DASH": DASH}, indent=1, default=str).encode("utf-8"),
                           "nifty_option_settings.json", "application/json", key="dl_settings_json")
        up = st.file_uploader("Saved Settings JSON Upload Karein", type=["json"], key="up_settings_json")
        if up is not None and st.button("Upload Ki Hui Settings Lagao", key="apply_settings_json"):
            try:
                n_set = apply_settings_dict(json.loads(up.getvalue().decode("utf-8")))
                st.success(f"{n_set} settings lag gayi. Page refresh ho raha hai...")
                st.rerun()
            except Exception as e:
                st.error(f"Settings file padhne me error: {e}")


def run_streamlit_desktop_app():
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(
        page_title="NIFTY OPTION SIGNAL PRO v28 - Full Desktop Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("NIFTY OPTION SIGNAL PRO v28 - Full Desktop Trading & Backtest Dashboard")

    load_saved_settings()  # pehle save ki hui settings (agar hain) wapas lagao

    with st.sidebar:
        # ---- Page navigation: Home + Scanner (dono ek hi app me) ----
        try:
            st.page_link("app.py", label="Home (Dashboard)", icon="ðŸ ")
            st.page_link("pages/1_Scanner.py", label="Scanner", icon="ðŸ”")
            st.divider()
        except Exception:
            pass
        save_slot = st.empty()  # Save button yahin (sabse upar) dikhega, kaam sidebar ke end me hota hai
        st.header("1. Broker & API Credentials")
        broker_choice = st.selectbox("Select Broker", ["DHAN", "UPSTOX"], index=0 if CONFIG["BROKER"] == "DHAN" else 1)
        CONFIG["BROKER"] = broker_choice
        chart_sym = st.selectbox("Chart Symbol", ["NIFTY_SPOT", "NIFTY_FUT"], index=0 if CONFIG["CHART_SYMBOL"] == "NIFTY_SPOT" else 1)
        CONFIG["CHART_SYMBOL"] = chart_sym

        if broker_choice == "DHAN":
            default_cid = "" if CONFIG["DHAN_CLIENT_ID"] == "YOUR_DHAN_CLIENT_ID" else CONFIG["DHAN_CLIENT_ID"]
            default_tok = "" if CONFIG["DHAN_ACCESS_TOKEN"] == "YOUR_DHAN_ACCESS_TOKEN" else CONFIG["DHAN_ACCESS_TOKEN"]
            dhan_cid = st.text_input("Dhan Client ID", value=st.secrets.get("DHAN_CLIENT_ID", default_cid))
            dhan_tok = st.text_input("Dhan Daily Access Token", value=st.secrets.get("DHAN_ACCESS_TOKEN", default_tok), type="password")
            CONFIG["DHAN_CLIENT_ID"] = dhan_cid.strip()
            CONFIG["DHAN_ACCESS_TOKEN"] = dhan_tok.strip()
        else:
            default_utok = "" if CONFIG["UPSTOX_ACCESS_TOKEN"] == "YOUR_UPSTOX_ACCESS_TOKEN" else CONFIG["UPSTOX_ACCESS_TOKEN"]
            up_tok = st.text_input("Upstox Access Token", value=st.secrets.get("UPSTOX_ACCESS_TOKEN", default_utok), type="password")
            CONFIG["UPSTOX_ACCESS_TOKEN"] = up_tok.strip()

        tg_bot = st.text_input("Telegram Bot Token (Optional)", value=st.secrets.get("TELEGRAM_BOT_TOKEN", CONFIG["TELEGRAM_BOT_TOKEN"]), type="password")
        tg_chat = st.text_input("Telegram Chat ID (Optional)", value=st.secrets.get("TELEGRAM_CHAT_ID", CONFIG["TELEGRAM_CHAT_ID"]))
        CONFIG["TELEGRAM_BOT_TOKEN"] = tg_bot.strip()
        CONFIG["TELEGRAM_CHAT_ID"] = tg_chat.strip()

        st.header("2. Execution Mode & Order Settings")
        run_mode = st.radio("Select Mode", ["LIVE", "BACKTEST", "REAL_TRADE_REPORT"], index=0)
        CONFIG["RUN_MODE"] = run_mode

        if run_mode == "LIVE":
            paper_on = st.checkbox("PAPER TRADING (virtual orders, real option LTP par)", value=CONFIG["PAPER_TRADING"])
            CONFIG["PAPER_TRADING"] = paper_on
            if paper_on:
                CONFIG["PAPER_CAPITAL"] = st.number_input("Paper Capital (Rs)", min_value=10000.0, value=float(CONFIG["PAPER_CAPITAL"]), step=10000.0)
                CONFIG["PAPER_BROKERAGE_PER_ORDER"] = st.number_input("Paper Brokerage per Order (Rs)", min_value=0.0, value=float(CONFIG["PAPER_BROKERAGE_PER_ORDER"]), step=5.0)
                CONFIG["PAPER_SLIPPAGE_PTS"] = st.number_input("Paper Slippage (option pts per fill)", min_value=0.0, value=float(CONFIG["PAPER_SLIPPAGE_PTS"]), step=0.5)
            auto_order = st.checkbox("AUTO PLACE LIVE BROKER ORDER (Blue Arrow)?", value=CONFIG["AUTO_PLACE_ORDER"])
            CONFIG["AUTO_PLACE_ORDER"] = auto_order
            if auto_order:
                st.error("LIVE ORDER EXECUTION ON: Real orders will be placed on broker!")
            else:
                st.info("SAFE MODE: Only Alerts, Dashboard & Journal Logging (No real order).")
            if CONFIG.get("PAPER_TRADING", False):
                CONFIG["AUTO_PLACE_ORDER"] = False  # paper ON ho to real order kabhi nahi jayega
                st.success("PAPER TRADING ON: Blue Arrow par virtual BUY/SELL lagega. Broker ko koi real order nahi jayega.")
        elif run_mode == "BACKTEST":
            bt_days = st.number_input("Backtest Days", min_value=5, max_value=180, value=int(CONFIG["BACKTEST_DAYS"]))
            CONFIG["BACKTEST_DAYS"] = int(bt_days)
            bt_entry = st.selectbox("Backtest Entry Type", ["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"], index=["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"].index(CONFIG["BACKTEST_ENTRY_TYPE"]))
            CONFIG["BACKTEST_ENTRY_TYPE"] = bt_entry

        st.header("3. Strike, Expiry & Target Exit")
        PARAMS["strikeMode"] = st.selectbox("Strike Selection", ["ATM", "ITM_1", "ITM_2", "OTM_1"], index=["ATM", "ITM_1", "ITM_2", "OTM_1"].index(PARAMS["strikeMode"]))
        PARAMS["expiryMode"] = st.selectbox("Expiry Selection", ["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"], index=["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"].index(PARAMS["expiryMode"]))
        if PARAMS["expiryMode"] == "MANUAL":
            PARAMS["manualExpiry"] = st.text_input("Manual Expiry (YYYY-MM-DD)", value=PARAMS["manualExpiry"])
        PARAMS["exitMode"] = st.selectbox("Target Exit Mode", ["T1", "T2", "T1_T2", "MANUAL"], index=["T1", "T2", "T1_T2", "MANUAL"].index(PARAMS["exitMode"]))
        if PARAMS["exitMode"] == "T1_T2":
            PARAMS["t1ExitPct"] = st.slider("T1 Partial Exit %", min_value=10, max_value=90, value=int(PARAMS["t1ExitPct"]), step=10)
        PARAMS["useHighLowForTarget"] = st.checkbox("Use Candle High/Low for Target Touch?", value=PARAMS["useHighLowForTarget"])

        st.header("4. G5: Green/Red Arrow Ke Baad Final Buy (Blue Arrow)")
        PARAMS["wfOn"] = st.checkbox("Final Buy (Blue Arrow) ON/OFF", value=PARAMS["wfOn"])
        PARAMS["wfRule"] = st.selectbox(
            "Final Buy Calculation Rule",
            ["E", "A", "B", "C", "D"],
            index=["E", "A", "B", "C", "D"].index(PARAMS["wfRule"]),
            help="E=Simple Dip+Rev | A=Dip+ATR Bounce | B=Signal Close Break | C=Dip+Wick | D=Fast/Slow MA Cross"
        )
        PARAMS["wfMin"] = st.number_input("Min Wait Candles After Signal", min_value=1, max_value=15, value=int(PARAMS["wfMin"]))
        PARAMS["wfMax"] = st.number_input("Max Wait Candles (Cancel Timeout)", min_value=5, max_value=50, value=int(PARAMS["wfMax"]))
        PARAMS["wfA"] = st.number_input("Rule A: Bounce ATR(10) Mult", min_value=0.1, max_value=3.0, value=float(PARAMS["wfA"]), step=0.1)
        PARAMS["wfDip"] = st.number_input("Rule C: Min Dip ATR(10) Mult", min_value=0.1, max_value=3.0, value=float(PARAMS["wfDip"]), step=0.1)
        PARAMS["wfWk"] = st.number_input("Rule C: Reversal Candle Wick %", min_value=10, max_value=90, value=int(PARAMS["wfWk"]))
        PARAMS["wfF"] = st.number_input("Rule D: Fast MA Length", min_value=2, max_value=20, value=int(PARAMS["wfF"]))
        PARAMS["wfS"] = st.number_input("Rule D: Slow MA Length", min_value=3, max_value=30, value=int(PARAMS["wfS"]))
        PARAMS["wfUp"] = st.number_input("No-Dip Breakout ATR Mult (0=OFF)", min_value=0.0, max_value=3.0, value=float(PARAMS["wfUp"]), step=0.1)
        PARAMS["wfUpPts"] = st.number_input("No-Dip Fixed Points Breakout (0=ATR)", min_value=0.0, max_value=200.0, value=float(PARAMS["wfUpPts"]), step=5.0)
        PARAMS["wfWick"] = st.checkbox("Cancel Watch if Wick Touches SL?", value=PARAMS["wfWick"])

        st.header("5. G7: Day Candle 20MA Back Direction Gate (7d / 5d)")
        PARAMS["dgOn"] = st.checkbox("Daily 20MA Direction Gate ON/OFF", value=PARAMS["dgOn"])
        PARAMS["dgMode"] = st.selectbox("Daily 20MA Gate Mode", ["Sirf PE par", "Dono (CE + PE)", "Sirf CE par"], index=["Sirf PE par", "Dono (CE + PE)", "Sirf CE par"].index(PARAMS["dgMode"]))
        PARAMS["dgLen"] = st.number_input("Daily Moving Average Length", min_value=5, max_value=100, value=int(PARAMS["dgLen"]))
        PARAMS["dgD1"] = st.number_input("Check 1: Daily Candles Back (e.g. 7)", min_value=1, max_value=30, value=int(PARAMS["dgD1"]))
        PARAMS["dgD2"] = st.number_input("Check 2: Daily Candles Back (e.g. 5)", min_value=1, max_value=30, value=int(PARAMS["dgD2"]))
        PARAMS["dgFlat"] = st.number_input("Daily MA Flat % Threshold", min_value=0.01, max_value=1.0, value=float(PARAMS["dgFlat"]), step=0.01)
        PARAMS["peScMin"] = st.slider("PE Direction Score Min (0-5)", min_value=0, max_value=5, value=int(PARAMS["peScMin"]))
        PARAMS["peBelowOpen"] = st.checkbox("PE Only Below Today Open", value=PARAMS["peBelowOpen"])

        st.header("6. Capital, Risk, Lot & Time Window")
        PARAMS["optLot"] = st.number_input("Lot Size", min_value=1, value=int(PARAMS["optLot"]))
        PARAMS["optDelta"] = st.number_input("Option Delta", min_value=0.1, max_value=1.0, value=float(PARAMS["optDelta"]), step=0.05)
        PARAMS["capital"] = st.number_input("Capital (Rs)", min_value=10000.0, value=float(PARAMS["capital"]), step=10000.0)
        PARAMS["riskPct"] = st.number_input("Risk Per Trade (%)", min_value=0.1, max_value=10.0, value=float(PARAMS["riskPct"]), step=0.1)
        PARAMS["slMult"] = st.number_input("SL ATR Multiplier", min_value=0.5, max_value=5.0, value=float(PARAMS["slMult"]), step=0.1)
        PARAMS["rrT"] = st.number_input("Target 1 Risk:Reward", min_value=0.5, max_value=10.0, value=float(PARAMS["rrT"]), step=0.5)
        PARAMS["extMult"] = st.number_input("EMA21 Peak Chase ATR Mult", min_value=0.5, max_value=10.0, value=float(PARAMS["extMult"]), step=0.5)
        PARAMS["orBars"] = st.number_input("Opening Range Bars (5m)", min_value=1, max_value=12, value=int(PARAMS["orBars"]))
        PARAMS["sess_start"] = st.text_input("Session Start (HH:MM IST)", value=PARAMS["sess_start"])
        PARAMS["sess_end"] = st.text_input("Session End (HH:MM IST)", value=PARAMS["sess_end"])
        PARAMS["coolBars"] = st.number_input("Cooldown Bars after Exit", min_value=0, max_value=50, value=int(PARAMS["coolBars"]))

        st.header("7. Direction & MTF Settings (3m / 5m / 15m / 1h / 4h)")
        c1, c2 = st.columns(2)
        with c1: PARAMS["allowCE"] = st.checkbox("Allow CE (Long)", value=PARAMS["allowCE"])
        with c2: PARAMS["allowPE"] = st.checkbox("Allow PE (Short)", value=PARAMS["allowPE"])
        PARAMS["needN"] = st.slider("Min 5m Conditions (of 5)", min_value=2, max_value=5, value=int(PARAMS["needN"]))
        PARAMS["mtfOn"] = st.checkbox("Enable MTF Filter (3m+5m)", value=PARAMS["mtfOn"])
        PARAMS["mtf15Req"] = st.checkbox("Require 15m Agreement?", value=PARAMS["mtf15Req"])
        PARAMS["mtfNeed"] = st.slider("Min MTF Conditions (of 4)", min_value=1, max_value=4, value=int(PARAMS["mtfNeed"]))
        PARAMS["peHtf"] = st.selectbox("PE HTF Requirement", ["OFF", "1h PE", "1h + 4h PE"], index=["OFF", "1h PE", "1h + 4h PE"].index(PARAMS["peHtf"]))
        PARAMS["peBrMax"] = st.number_input("PE Max Breadth Score", min_value=0.0, max_value=100.0, value=float(PARAMS["peBrMax"]))
        PARAMS["peAdxMin"] = st.number_input("PE Min ADX (0 = OFF)", min_value=0.0, max_value=50.0, value=float(PARAMS["peAdxMin"]))

        st.header("8. ADX & DI+ / DI- Filters")
        PARAMS["adxOn"] = st.checkbox("Enable ADX Sideways Filter", value=PARAMS["adxOn"])
        PARAMS["adxLen"] = st.number_input("ADX Length", min_value=5, max_value=50, value=int(PARAMS["adxLen"]))
        PARAMS["adxMin"] = st.number_input("Min ADX (Avoid Sideways)", min_value=5.0, max_value=50.0, value=float(PARAMS["adxMin"]))
        PARAMS["diOn"] = st.checkbox("Enable DI+ / DI- Filter", value=PARAMS["diOn"])
        PARAMS["diMtf"] = st.checkbox("Apply DI Filter on 3m & 15m", value=PARAMS["diMtf"])
        PARAMS["diNeed"] = st.slider("DI TF Pass Required (1-3)", min_value=1, max_value=3, value=int(PARAMS["diNeed"]))
        PARAMS["adxTrd"] = st.number_input("DI Trend Min ADX", min_value=5.0, max_value=50.0, value=float(PARAMS["adxTrd"]))
        PARAMS["diStrong"] = st.number_input("DI Strong Threshold", min_value=5.0, max_value=50.0, value=float(PARAMS["diStrong"]))
        PARAMS["diWeak"] = st.number_input("DI Weak Threshold", min_value=5.0, max_value=50.0, value=float(PARAMS["diWeak"]))

        st.header("9. Option OI, VOL PCR, Futures OI & Probability")
        PARAMS["autoOc"] = st.checkbox("Auto Option Chain OI", value=PARAMS["autoOc"])
        PARAMS["ocN"] = st.slider("Option OI Strike Span (+-N)", min_value=2, max_value=9, value=int(PARAMS["ocN"]))
        PARAMS["pcrBull"] = st.number_input("OI PCR Bullish >=", min_value=0.5, max_value=3.0, value=float(PARAMS["pcrBull"]), step=0.05)
        PARAMS["pcrBear"] = st.number_input("OI PCR Bearish <=", min_value=0.2, max_value=2.0, value=float(PARAMS["pcrBear"]), step=0.05)
        PARAMS["wallBuf"] = st.number_input("OI Wall Buffer %", min_value=0.05, max_value=2.0, value=float(PARAMS["wallBuf"]), step=0.05)
        PARAMS["ovOn"] = st.checkbox("Enable Option VOL PCR", value=PARAMS["ovOn"])
        PARAMS["ovN"] = st.slider("VOL PCR Strike Span (+-N)", min_value=2, max_value=9, value=int(PARAMS["ovN"]))
        PARAMS["ovFeed"] = st.checkbox("Feed VOL PCR into Probability", value=PARAMS["ovFeed"])
        PARAMS["futOiOn"] = st.checkbox("Enable Futures OI Analysis", value=PARAMS["futOiOn"])
        PARAMS["oiLook"] = st.number_input("Futures OI Lookback Bars", min_value=2, max_value=50, value=int(PARAMS["oiLook"]))
        PARAMS["oiProbFilterOn"] = st.checkbox("Enable OI+Vol Probability Filter", value=PARAMS["oiProbFilterOn"])
        PARAMS["minOiProbCE"] = st.number_input("Min OI+Vol Prob % for CE", min_value=0.0, max_value=100.0, value=float(PARAMS["minOiProbCE"]))
        PARAMS["minOiProbPE"] = st.number_input("Min OI+Vol Prob % for PE", min_value=0.0, max_value=100.0, value=float(PARAMS["minOiProbPE"]))
        PARAMS["requireHighProbOnly"] = st.checkbox("Trade HIGH PROB Signals Only?", value=PARAMS["requireHighProbOnly"])
        PARAMS["pcrIn"] = st.number_input("Manual OI PCR (0 = Auto)", min_value=0.0, max_value=5.0, value=float(PARAMS["pcrIn"]), step=0.05)
        PARAMS["callWall"] = st.number_input("Manual Call Wall (0 = Auto)", min_value=0.0, value=float(PARAMS["callWall"]), step=50.0)
        PARAMS["putWall"] = st.number_input("Manual Put Wall (0 = Auto)", min_value=0.0, value=float(PARAMS["putWall"]), step=50.0)

        st.header("10. Breadth (20 Heavyweight Stocks) & Sector Strength")
        PARAMS["hiTh"] = st.number_input("Breadth High Prob Threshold", min_value=50.0, max_value=95.0, value=float(PARAMS["hiTh"]))
        PARAMS["flatPct"] = st.number_input("Stock Flat % Threshold", min_value=0.0, max_value=1.0, value=float(PARAMS["flatPct"]), step=0.01)
        PARAMS["scOn"] = st.checkbox("Show Sector Strength Table", value=PARAMS["scOn"])
        PARAMS["scFeed"] = st.checkbox("Use Sector Strength Filter", value=PARAMS["scFeed"])
        PARAMS["scTh"] = st.number_input("Sector Strength % Threshold", min_value=0.05, max_value=2.0, value=float(PARAMS["scTh"]), step=0.05)
        PARAMS["scNeed"] = st.slider("Heavy Sectors Required (of 3)", min_value=1, max_value=3, value=int(PARAMS["scNeed"]))
        PARAMS["scBankOk"] = st.checkbox("Require Banks Alignment", value=PARAMS["scBankOk"])

        with st.expander("11. v22 Extra Filters (RSI, Volume, Level, VIX, Time, Expiry, Trail)"):
            PARAMS["lateOn"] = st.checkbox("Late-Entry Guard (High ADX+Breadth)", value=PARAMS["lateOn"])
            PARAMS["arOn"] = st.checkbox("ADX Rising Filter", value=PARAMS["arOn"])
            PARAMS["rsiOn"] = st.checkbox("RSI Cap Filter", value=PARAMS["rsiOn"])
            PARAMS["rsiHi"] = st.number_input("Max RSI for CE", value=float(PARAMS["rsiHi"]))
            PARAMS["rsiLo"] = st.number_input("Min RSI for PE", value=float(PARAMS["rsiLo"]))
            PARAMS["vfOn"] = st.checkbox("Volume Confirm Filter", value=PARAMS["vfOn"])
            PARAMS["vfMult"] = st.number_input("Volume 20-SMA Multiplier", value=float(PARAMS["vfMult"]), step=0.1)
            PARAMS["cdOn"] = st.checkbox("Candle Close Strength Filter", value=PARAMS["cdOn"])
            PARAMS["lvlOn"] = st.checkbox("PDH / PDL Level Guard", value=PARAMS["lvlOn"])
            PARAMS["rdOn"] = st.checkbox("100-pt Round Level Guard", value=PARAMS["rdOn"])
            PARAMS["opOn"] = st.checkbox("CE Only Above Today Open", value=PARAMS["opOn"])
            PARAMS["vxOn"] = st.checkbox("India VIX Filter", value=PARAMS["vxOn"])
            PARAMS["tmOn"] = st.checkbox("Blocked Time Windows Filter", value=PARAMS["tmOn"])
            PARAMS["exOn"] = st.checkbox("Skip Expiry Day", value=PARAMS["exOn"])
            PARAMS["exDay"] = st.selectbox("Expiry Weekday", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(PARAMS["exDay"]))
            PARAMS["beOn"] = st.checkbox("Move SL to Breakeven (+1R)", value=PARAMS["beOn"])
            PARAMS["trOn"] = st.checkbox("Trail SL on T1 to Target T2", value=PARAMS["trOn"])

        st.header("12. Dashboard 12-Table Display Settings")
        DASH["textSz"] = st.selectbox("Table Font Size", ["tiny", "small", "normal"], index=["tiny", "small", "normal"].index(DASH["textSz"]))
        DASH["showDetail"] = st.checkbox("Show Full Detail Rows", value=DASH["showDetail"])
        DASH["showLog"] = st.checkbox("Show Signal Log Table", value=DASH["showLog"])
        DASH["showList"] = st.checkbox("Show 20 Heavyweight Stocks Table", value=DASH["showList"])
        DASH["scAll"] = st.checkbox("Show All 15 Sectors Table", value=DASH["scAll"])
        DASH["jShow"] = st.checkbox("Show Trade Journal Table", value=DASH["jShow"])
        DASH["phShow"] = st.checkbox("Show Phase-Wise Stats Table", value=DASH["phShow"])
        DASH["xsShow"] = st.checkbox("Show Extra Stats Table", value=DASH["xsShow"])
        DASH["gdShow"] = st.checkbox("Show Setup Grade Table", value=DASH["gdShow"])
        DASH["vp_showTbl"] = st.checkbox("Show VOL PCR Table", value=DASH["vp_showTbl"])

        render_all_settings_panel(st)

        with save_slot.container():
            if st.button("ðŸ’¾ Save Settings", key="save_all_settings_btn", use_container_width=True):
                try:
                    n_saved = save_current_settings()
                    st.success(f"{n_saved} settings save ho gayi. Agli baar app khologe to yahi settings milengi.")
                except Exception as e:
                    st.error(f"Settings save nahi hui: {e}")
            elif os.path.exists(SETTINGS_SAVE_FILE):
                st.caption("Saved settings load hain. Kuchh badalo to upar Save dabao.")
            else:
                st.caption("Setting badalne ke baad Save dabao.")

    now_ist = dt.datetime.now(IST)
    st.info(
        f"**IST Time:** {now_ist.strftime('%Y-%m-%d %I:%M:%S %p')} | "
        f"**Mode:** {CONFIG['RUN_MODE']} | "
        f"**Strike:** {PARAMS['strikeMode']} | "
        f"**Expiry:** {PARAMS['expiryMode']} | "
        f"**Exit:** {PARAMS['exitMode']} | "
        f"**FinalBuy:** {'ON (' + PARAMS['wfRule'] + ')' if PARAMS['wfOn'] else 'OFF'} | "
        f"**Daily 20MA:** {'ON (' + str(PARAMS['dgD1']) + 'd/' + str(PARAMS['dgD2']) + 'd)' if PARAMS['dgOn'] else 'OFF'}"
    )

    if run_mode == "REAL_TRADE_REPORT":
        st.subheader("Real Live Trades Journal Report")
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        if os.path.exists(csv_file):
            df_rep = pd.read_csv(csv_file)
            st.dataframe(df_rep, use_container_width=True)
            st.download_button("Download Real Trades CSV", df_rep.to_csv(index=False).encode("utf-8"), csv_file, "text/csv")
        else:
            st.warning("Abhi tak koi Real Trade record file nahi bani hai (0 Real Trades).")
        if (os.path.exists(CONFIG.get("PAPER_STATE_JSON", "paper_open_positions.json"))
                or os.path.exists(CONFIG.get("PAPER_TRADES_CSV", "paper_trades_journal.csv"))):
            paper_panel_streamlit(None, key_prefix="rep")
        return

    creds_ok = (
        (broker_choice == "DHAN" and CONFIG["DHAN_CLIENT_ID"] and CONFIG["DHAN_ACCESS_TOKEN"]) or
        (broker_choice == "UPSTOX" and CONFIG["UPSTOX_ACCESS_TOKEN"])
    )
    if not creds_ok:
        st.warning("Sidebar mein apne Broker Credentials (Client ID aur Access Token) daalein.")
        return

    cred_sig = f"{broker_choice}_{CONFIG['DHAN_CLIENT_ID']}_{CONFIG['DHAN_ACCESS_TOKEN'][:10]}_{CONFIG['UPSTOX_ACCESS_TOKEN'][:10]}"
    if "broker_conn" not in st.session_state or st.session_state.get("cred_sig") != cred_sig:
        with st.spinner("Broker Master Scrip List load ho rahi hai..."):
            try:
                st.session_state.broker_conn = BrokerConnector(CONFIG)
                st.session_state.cred_sig = cred_sig
                st.success(f"{broker_choice} Broker Connected Successfully!")
            except Exception as e:
                st.error(f"Broker Connection Error: {e}")
                return

    connector = st.session_state.broker_conn

    with st.expander("Data Connection Test (Token / Data API check)"):
        if st.button("Test Data Now"):
            _t = connector.get_candles(CONFIG["CHART_SYMBOL"], interval="D", days=10)
            if _t.empty:
                st.error(f"Data nahi aaya. Reason: {connector.last_error or 'unknown (Security ID / token check karein)'}")
            else:
                st.success(f"OK: {len(_t)} daily bars, last close {_t['close'].iloc[-1]:.2f} ({_t.index[-1]:%Y-%m-%d})")

    if run_mode == "BACKTEST":
        st.subheader(f"Historical Backtest ({CONFIG['BACKTEST_DAYS']} Days | {CONFIG['BACKTEST_ENTRY_TYPE']})")
        if st.button("Run Full Multi-Timeframe Backtest Now", type="primary"):
            with st.spinner("3m, 5m, 15m, 1h, 4h, Daily, Futures, VIX aur 20 Heavyweight Stocks ka data fetch ho raha hai..."):
                bt_res = run_backtest(connector, days=CONFIG["BACKTEST_DAYS"])
            st.session_state["last_bt_res"] = bt_res
            st.session_state["last_bt_modes"] = ["ALL_SIGNALS", "REAL_BLUE_ONLY"] if CONFIG["BACKTEST_ENTRY_TYPE"] == "BOTH" else [CONFIG["BACKTEST_ENTRY_TYPE"]]
            st.session_state["last_bt_strike"] = PARAMS["strikeMode"]
            st.session_state["last_bt_exit"] = PARAMS["exitMode"]

        if "last_bt_res" in st.session_state:
            bt_res = st.session_state["last_bt_res"]
            if isinstance(bt_res, dict) and bt_res.get("error"):
                st.error(bt_res["error"])
            else:
                st.success(f"Backtest Complete! (Total 5m Candles Processed: {bt_res.get('bars_5m', 'OK') if isinstance(bt_res, dict) else 'OK'})")
                for m_lbl in st.session_state.get("last_bt_modes", []):
                    csv_name = f"backtest_{m_lbl}_{st.session_state.get('last_bt_strike', PARAMS['strikeMode'])}_{st.session_state.get('last_bt_exit', PARAMS['exitMode'])}.csv"
                    html_name = f"dashboard_backtest_{m_lbl}.html"
                    st.markdown(f"### Results: {m_lbl}")
                    c_dl1, c_dl2 = st.columns(2)
                    if os.path.exists(csv_name):
                        j_df = pd.read_csv(csv_name)
                        with c_dl1:
                            st.download_button(f"Download {csv_name} ({len(j_df)} trades)", j_df.to_csv(index=False).encode("utf-8"), csv_name, "text/csv", key=f"dl_csv_{m_lbl}")
                        st.dataframe(j_df, use_container_width=True)
                        if "PremiumSrc" in j_df.columns:
                            st.caption("PremiumSrc: *_REAL / DHAN_ROLLING = broker ka real option price | EST_BS = estimate (Black-Scholes + India VIX) | "
                                       "ExpiryDateSrc: MASTER = broker list se confirm, RULE_EST = expired contract, weekday rule se nikali date. "
                                       "EntryPx/ExitPx = Nifty spot level.")
                    else:
                        st.warning(f"File {csv_name} generate nahi hui.")

                    if os.path.exists(html_name):
                        with open(html_name, "r", encoding="utf-8") as hf:
                            html_str = hf.read()
                        with c_dl2:
                            st.download_button(f"Download {html_name}", html_str, html_name, "text/html", key=f"dl_html_{m_lbl}")
                        components.html(html_str, height=780, scrolling=True)
                    else:
                        st.warning(f"Dashboard {html_name} generate nahi hua (paryapt daily/MTF bars nahi mile).")
    else:
        if "live_engine" not in st.session_state:
            st.session_state.live_engine = NiftyOptionProEngine(connector, is_backtest=False)
        engine = st.session_state.live_engine

        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
        with c_btn1: run_now = st.button("Fetch & Evaluate Live Bar Now", type="primary")
        with c_btn2: auto_live = st.checkbox("Auto-Refresh Live (Every 30s)", value=False)
        with c_btn3:
            if st.button("Manual Exit Active Trade"):
                df_now = connector.get_candles(CONFIG["CHART_SYMBOL"], interval="5", days=1)
                if not df_now.empty:
                    engine.manual_exit_now(df_now["close"].iloc[-1], dt.datetime.now(IST), reason="MANUAL_EXIT")
                    st.success("Manual Exit Executed!")
                else: st.warning("Active trade nahi hai ya data nahi mila.")
        with c_btn4:
            if st.button("Reset Engine State"):
                st.session_state.live_engine = NiftyOptionProEngine(connector, is_backtest=False)
                st.success("Engine State Reset!")

        if run_now or auto_live:
            with st.spinner("Live 3m/5m/15m/1h/4h, Option Chain OI, VOL PCR & 20 Heavyweight Stocks fetch ho rahe hain..."):
                try:
                    engine.process_live_bar(is_pre_alert=False)
                except Exception as exc:
                    st.error(f"Live Bar Evaluation Error: {exc}")

        dash_file = CONFIG.get("DASH_HTML_PATH", "dashboard.html")
        if os.path.exists(dash_file):
            with open(dash_file, "r", encoding="utf-8") as f:
                dash_html = f.read()
            st.subheader("Live Candlestick Chart + All 12 Pine Script Tables")
            st.download_button("Download Live dashboard.html", dash_html, "dashboard.html", "text/html", key="dl_live_html")
            components.html(dash_html, height=820, scrolling=True)
        else:
            st.info("Upar 'Fetch & Evaluate Live Bar Now' button dabayein â€” chart aur saari 12 tables yahan load ho jayengi.")

        if engine.trade_journal:
            st.subheader("Session Trade Journal")
            st.dataframe(pd.DataFrame(engine.trade_journal), use_container_width=True)

        if (CONFIG.get("PAPER_TRADING", False)
                or os.path.exists(CONFIG.get("PAPER_STATE_JSON", "paper_open_positions.json"))
                or os.path.exists(CONFIG.get("PAPER_TRADES_CSV", "paper_trades_journal.csv"))):
            paper_panel_streamlit(connector, key_prefix="live")

        if auto_live:
            time.sleep(30)
            st.rerun()

if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            run_streamlit_desktop_app()
        else:
            raise RuntimeError("Not in Streamlit context")
    except Exception:
        connector = BrokerConnector(CONFIG)
        interactive_option_selector(connector)
        if CONFIG["RUN_MODE"].upper() == "BACKTEST":
            run_backtest(connector, days=CONFIG["BACKTEST_DAYS"])
        else:
            engine = NiftyOptionProEngine(connector, is_backtest=False)
            while True:
                now = dt.datetime.now(IST)
                if PARAMS["preSec"] > 0 and (now.minute % 5 == 4) and (now.second == 60 - PARAMS["preSec"]):
                    try: engine.process_live_bar(is_pre_alert=True)
                    except Exception: pass
                    time.sleep(1)
                if (now.minute % 5 == 0) and (now.second == 2):
                    try: engine.process_live_bar(is_pre_alert=False)
                    except Exception as exc: print(f"[Error] {exc}")
                    time.sleep(2)
                time.sleep(0.5)
