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
      (browser me kholo, har 20 sec auto refresh; chart library CDN se aati hai).
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

PARAMS = {
    "strikeMode": "ATM",
    "expiryMode": "CURRENT_WEEK",
    "manualExpiry": "",
    "exitMode": "T1",
    "t1ExitPct": 50,
    "useHighLowForTarget": True,
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
    "mtfOn": True,
    "mtf15Req": False,
    "mtfNeed": 3,
    "adxOn": True,
    "adxLen": 14,
    "adxMin": 20.0,
    "diOn": True,
    "diMtf": True,
    "diNeed": 2,
    "adxTrd": 20.0,
    "diStrong": 20.0,
    "diWeak": 20.0,
    "allowCE": True,
    "allowPE": True,
    "peBrMax": 100.0,
    "peAdxMin": 0.0,
    "peHtf": "1h PE",
    "peBelowOpen": True,
    "optSym": "",
    "optEntry": 0.0,
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
    "dgOn": True,
    "dgMode": "Sirf PE par",
    "peScMin": 3,
    "dgLen": 20,
    "dgD1": 7,
    "dgD2": 5,
    "dgFlat": 0.05,
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
    "preSec": 15,
    "flatPct": 0.02,
    "implRef": 0.5,
    "hiTh": 65.0,
    "scOn": True,
    "scTh": 0.25,
    "scFeed": False,
    "scNeed": 2,
    "scBankOk": True,
}

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

def clamp_strike_span(n: int) -> int: return max(2, min(9, int(n)))

def get_trade_strike(spot_price: float, side: str) -> float:
    step = PARAMS["optStep"]
    atm = round(spot_price / step) * step
    mode = PARAMS["strikeMode"].upper()
    if mode == "ITM_1": return (atm - step) if side == "CE" else (atm + step)
    elif mode == "ITM_2": return (atm - 2 * step) if side == "CE" else (atm + 2 * step)
    elif mode == "OTM_1": return (atm + step) if side == "CE" else (atm - step)
    return atm

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

def parse_hhmm(t_str: str) -> dt.time:
    h, m = map(int, t_str.split(":"))
    return dt.time(h, m)

def in_session(ts: dt.datetime, start_str: str, end_str: str) -> bool:
    t = ts.time()
    return parse_hhmm(start_str) <= t <= parse_hhmm(end_str)

def calc_ema(series: pd.Series, length: int) -> pd.Series: return series.ewm(span=length, adjust=False).mean()
def calc_sma(series: pd.Series, length: int) -> pd.Series: return series.rolling(window=length).mean()
def calc_rma(series: pd.Series, length: int) -> pd.Series: return series.ewm(alpha=1.0 / length, adjust=False).mean()

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
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return calc_rma(tr, length)

def calc_dmi(df: pd.DataFrame, length: int = 14):
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff(); down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
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
    final_ub = np.zeros(n); final_lb = np.zeros(n); sdir = np.ones(n)
    for i in range(n):
        if i == 0:
            final_ub[i] = upperband[i]; final_lb[i] = lowerband[i]; sdir[i] = 1; continue
        final_ub[i] = upperband[i] if (upperband[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]) else final_ub[i-1]
        final_lb[i] = lowerband[i] if (lowerband[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]) else final_lb[i-1]
        if sdir[i-1] == 1 and close[i] > final_ub[i-1]: sdir[i] = -1
        elif sdir[i-1] == -1 and close[i] < final_lb[i-1]: sdir[i] = 1
        else: sdir[i] = sdir[i-1]
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
                try: self.dhan = dhanhq(cid, token)
                except Exception as e2:
                    last_err = e2
                    try: self.dhan = dhanhq(client_id=cid, access_token=token)
                    except Exception as e3:
                        try: self.dhan = dhanhq(token)
                        except Exception as e4:
                            raise RuntimeError(f"Dhan init failed: {last_err} | {e2} | {e3} | {e4}")
        elif self.broker == "UPSTOX":
            self.headers = {"Accept": "application/json", "Authorization": f"Bearer {str(cfg['UPSTOX_ACCESS_TOKEN']).strip()}"}
        else:
            raise ValueError("BROKER sirf 'DHAN' ya 'UPSTOX' hona chahiye.")
        self.inst = self._load_master()

    def _load_master(self) -> dict:
        m = {}
        if self.broker == "DHAN":
            df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
            idx = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_TRADING_SYMBOL"] == "NIFTY")]
            if not idx.empty: m["NIFTY_SPOT"] = str(idx.iloc[0]["SEM_SMST_SECURITY_ID"])
            vix = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_TRADING_SYMBOL"] == "INDIA VIX")]
            if not vix.empty: m["INDIAVIX"] = str(vix.iloc[0]["SEM_SMST_SECURITY_ID"])
            fut = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "FUTIDX") & (df["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-"))].sort_values("SEM_EXPIRY_DATE")
            if not fut.empty: m["NIFTY_FUT"] = str(fut.iloc[0]["SEM_SMST_SECURITY_ID"])
            eq = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")]
            for sym, _ in BREADTH_STOCKS:
                row = eq[eq["SEM_TRADING_SYMBOL"] == sym]
                if not row.empty: m[sym] = str(row.iloc[0]["SEM_SMST_SECURITY_ID"])
            m["_DF"] = df
        elif self.broker == "UPSTOX":
            df = pd.read_json("https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz", compression="gzip")
            m["NIFTY_SPOT"] = "NSE_INDEX|Nifty 50"
            m["INDIAVIX"] = "NSE_INDEX|India VIX"
            fut = df[(df["segment"] == "NSE_FO") & (df["instrument_type"] == "FUT") & (df["name"] == "NIFTY")].sort_values("expiry")
            if not fut.empty: m["NIFTY_FUT"] = fut.iloc[0]["instrument_key"]
            eq = df[df["segment"] == "NSE_EQ"]
            for sym, _ in BREADTH_STOCKS:
                row = eq[eq["trading_symbol"] == sym]
                if not row.empty: m[sym] = row.iloc[0]["instrument_key"]
            m["_DF"] = df
        return m

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
        if mode == "MANUAL" and PARAMS["manualExpiry"].strip(): return PARAMS["manualExpiry"].strip()
        exps = self.get_all_upcoming_expiries()
        if not exps: return ""
        if mode == "NEXT_WEEK" and len(exps) > 1: return exps[1]
        if mode == "MONTHLY":
            cur_ym = exps[0][:7]
            month_exps = [e for e in exps if e.startswith(cur_ym)]
            return month_exps[-1] if month_exps else exps[0]
        return exps[0]

    def get_candles(self, key: str, interval: str = "5", days: int = 10) -> pd.DataFrame:
        to_dt = dt.datetime.now(IST); from_dt = to_dt - dt.timedelta(days=days)
        if self.broker == "DHAN":
            sec_id = self.inst.get(key)
            if not sec_id: return pd.DataFrame()
            seg = "IDX_I" if key in ("NIFTY_SPOT", "INDIAVIX") else ("NSE_FNO" if key == "NIFTY_FUT" else "NSE_EQ")
            itype = "INDEX" if seg == "IDX_I" else ("FUTIDX" if seg == "NSE_FNO" else "EQUITY")
            if interval == "D":
                res = self.dhan.historical_daily_data(security_id=sec_id, exchange_segment=seg, instrument_type=itype, from_date=from_dt.strftime("%Y-%m-%d"), to_date=to_dt.strftime("%Y-%m-%d"))
            else:
                req_int = "1" if interval == "3" else ("60" if interval == "240" else interval)
                res = self.dhan.intraday_minute_data(security_id=sec_id, exchange_segment=seg, instrument_type=itype, from_date=from_dt.strftime("%Y-%m-%d 09:15:00"), to_date=to_dt.strftime("%Y-%m-%d 15:30:00"), interval=int(req_int))
            d = res.get("data", {})
            if not d or "timestamp" not in d or len(d["timestamp"]) == 0: return pd.DataFrame()
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert(IST),
                "open": d["open"], "high": d["high"], "low": d["low"], "close": d["close"],
                "volume": d.get("volume", [0] * len(d["close"])),
                "oi": d.get("open_interest", [0] * len(d["close"]))
            }).set_index("timestamp").sort_index()
        elif self.broker == "UPSTOX":
            ikey = self.inst.get(key)
            if not ikey: return pd.DataFrame()
            umap = {"1": ("minutes", "1"), "3": ("minutes", "1"), "5": ("minutes", "5"), "15": ("minutes", "15"), "60": ("hours", "1"), "240": ("hours", "1"), "D": ("days", "1")}
            utype, uval = umap[interval]
            r1 = requests.get(f"https://api.upstox.com/v3/historical-candle/{ikey}/{utype}/{uval}/{to_dt.strftime('%Y-%m-%d')}/{from_dt.strftime('%Y-%m-%d')}", headers=self.headers, timeout=10).json()
            c_hist = r1.get("data", {}).get("candles", [])
            c_intra = []
            if interval != "D":
                r2 = requests.get(f"https://api.upstox.com/v3/historical-candle/intraday/{ikey}/{utype}/{uval}", headers=self.headers, timeout=10).json()
                c_intra = r2.get("data", {}).get("candles", [])
            rows = c_intra + c_hist
            if not rows: return pd.DataFrame()
            df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(IST)
            df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").set_index("timestamp")

        if interval in ("3", "240") and not df.empty:
            rule = "3min" if interval == "3" else "240min"
            df = df.resample(rule, origin="start_day", offset="15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "oi": "last"}).dropna(subset=["close"])
        return df

    def get_breadth_changes(self) -> dict:
        out = {}
        for sym, _ in BREADTH_STOCKS:
            df_d = self.get_candles(sym, interval="D", days=6)
      
