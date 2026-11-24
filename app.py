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
# 4. BROKER CONNECTOR
# ==============================================================================
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
         
