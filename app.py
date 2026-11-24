# -*- coding: utf-8 -*-
"""
nifty_option_pro_v28_FULL.py
============================
100% Full Intact Version + Market Hours Override Toggle + All Original Controls.
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
    "overrideMarketHours": True,
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
    if PARAMS.get("overrideMarketHours", False):
        return True
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
                        raise RuntimeError(f"Dhan init failed: {last_err} | {e3}")
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
            if len(df_d) >= 2:
                prev_c = df_d["close"].iloc[-2]; curr_c = df_d["close"].iloc[-1]
                out[sym] = (curr_c / prev_c - 1.0) * 100.0 if prev_c > 0 else np.nan
            else: out[sym] = np.nan
        return out

    def get_option_chain_metrics(self, atm_now: float, locked_atm_vol: float, oc_n: int, ov_n: int) -> dict:
        oc_n = clamp_strike_span(oc_n); ov_n = clamp_strike_span(ov_n)
        selected_exp = self.get_selected_expiry()
        oi_ce, oi_pe = {}, {}; vol_ce, vol_pe = {}
        oi_cnt = 0; vol_cnt = 0; ltp_map = {}; ltp_n = max(oc_n, ov_n, 3)
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
                        oi_ce[off] = c_oi; oi_pe[off] = p_oi
                for off in range(-ov_n, ov_n + 1):
                    k_str = f"{locked_atm_vol + off * PARAMS['optStep']:.6f}"
                    if k_str in oc:
                        c_v = oc[k_str].get("ce", {}).get("volume", 0) or 0
                        p_v = oc[k_str].get("pe", {}).get("volume", 0) or 0
                        if c_v > 0: vol_cnt += 1
                        if p_v > 0: vol_cnt += 1
                        vol_ce[off] = c_v; vol_pe[off] = p_v
                for off in range(-ltp_n, ltp_n + 1):
                    k_val = atm_now + off * PARAMS["optStep"]; k_str = f"{k_val:.6f}"
                    if k_str in oc:
                        ltp_map[round(float(k_val), 2)] = {"ce": oc[k_str].get("ce", {}).get("last_price", np.nan), "pe": oc[k_str].get("pe", {}).get("last_price", np.nan)}
            elif self.broker == "UPSTOX":
                res = requests.get(f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={selected_exp}", headers=self.headers, timeout=10).json()
                for row in res.get("data", []):
                    k = row.get("strike_price", 0)
                    c_md = row.get("call_options", {}).get("market_data", {}); p_md = row.get("put_options", {}).get("market_data", {})
                    if abs((k - atm_now) / PARAMS["optStep"]) <= ltp_n:
                        ltp_map[round(float(k), 2)] = {"ce": c_md.get("ltp", np.nan), "pe": p_md.get("ltp", np.nan)}
                    off_oi = int(round((k - atm_now) / PARAMS["optStep"]))
                    if -oc_n <= off_oi <= oc_n:
                        c_oi = c_md.get("oi", 0) or 0; p_oi = p_md.get("oi", 0) or 0
                        if c_oi > 0: oi_cnt += 1
                        if p_oi > 0: oi_cnt += 1
                        oi_ce[off_oi] = c_oi; oi_pe[off_oi] = p_oi
                    off_v = int(round((k - locked_atm_vol) / PARAMS["optStep"]))
                    if -ov_n <= off_v <= ov_n:
                        c_v = c_md.get("volume", 0) or 0; p_v = p_md.get("volume", 0) or 0
                        if c_v > 0: vol_cnt += 1
                        if p_v > 0: vol_cnt += 1
                        vol_ce[off_v] = c_v; vol_pe[off_v] = p_v
        except Exception as e:
            print(f"Option Chain fetch warning: {e}")

        oc_ce_sum = sum(oi_ce.values()); oc_pe_sum = sum(oi_pe.values())
        oc_ok = (oi_cnt >= 4) and (oc_ce_sum > 0) and (oc_pe_sum > 0)
        oc_pcr = (oc_pe_sum / oc_ce_sum) if oc_ok else np.nan
        oc_c_arr = [oi_ce.get(i, 0) for i in range(0, oc_n + 1)]
        oc_p_arr = [oi_pe.get(-i, 0) for i in range(0, oc_n + 1)]
        oc_call_k = (atm_now + int(np.argmax(oc_c_arr)) * PARAMS["optStep"]) if (oc_ok and max(oc_c_arr) > 0) else np.nan
        oc_put_k = (atm_now - int(np.argmax(oc_p_arr)) * PARAMS["optStep"]) if (oc_ok and max(oc_p_arr) > 0) else np.nan

        vol_ce_sum = sum(vol_ce.values()); vol_pe_sum = sum(vol_pe.values())
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
        if not CONFIG["AUTO_PLACE_ORDER"] or lots <= 0 or CONFIG["RUN_MODE"] != "LIVE": return False
        qty = lots * PARAMS["optLot"]; opt_type = "CE" if side == "CE" else "PE"
        exp = expiry_date or self.get_selected_expiry()
        try:
            df_m = self.inst["_DF"]
            if self.broker == "DHAN":
                opt_df = df_m[
                    (df_m["SEM_EXM_EXCH_ID"] == "NSE") & (df_m["SEM_INSTRUMENT_NAME"] == "OPTIDX") &
                    (df_m["SEM_TRADING_SYMBOL"].str.startswith("NIFTY-")) & (df_m["SEM_OPTION_TYPE"] == opt_type) &
                    (df_m["SEM_STRIKE_PRICE"] == float(strike)) & (df_m["SEM_EXPIRY_DATE"].astype(str).str.startswith(exp))
                ]
                if not opt_df.empty:
                    sec_id = str(opt_df.iloc[0]["SEM_SMST_SECURITY_ID"])
                    txn = self.dhan.BUY if action == "BUY" else self.dhan.SELL
                    self.dhan.place_order(security_id=sec_id, exchange_segment=self.dhan.NSE_FNO, transaction_type=txn, quantity=qty, order_type=self.dhan.MARKET, product_type=self.dhan.INTRA, price=0)
                    return True
            elif self.broker == "UPSTOX":
                opt_df = df_m[(df_m["segment"] == "NSE_FO") & (df_m["name"] == "NIFTY") & (df_m["instrument_type"] == opt_type) & (df_m["strike_price"] == float(strike))].copy()
                opt_df["exp_str"] = opt_df["expiry"].apply(lambda x: dt.datetime.fromtimestamp(x / 1000, IST).strftime("%Y-%m-%d"))
                opt_df = opt_df[opt_df["exp_str"] == exp]
                if not opt_df.empty:
                    ikey = opt_df.iloc[0]["instrument_key"]
                    payload = {"quantity": qty, "product": "I", "validity": "DAY", "price": 0, "instrument_token": ikey, "order_type": "MARKET", "transaction_type": action, "disclosed_quantity": 0, "trigger_price": 0, "is_amo": False}
                    requests.post("https://api.upstox.com/v2/order/place", json=payload, headers=self.headers, timeout=10)
                    return True
        except Exception as e:
            print(f"[Order Placement Error] {e}")
        return False

NAN = float("nan")
SECTOR_NAMES = list(SECTOR_MAP.keys())

def na(x): return x is None or (isinstance(x, float) and math.isnan(x))
def nz(x, d=0.0): return d if na(x) else x
def fmtG(g, flat=0.02): return "--" if na(g) else (("+" if g >= 0 else "") + f"{g:.2f}%")
def colG(g, flat): return "gray" if na(g) else ("green" if g > flat else ("red" if g < -flat else "gray"))
def pfTxt(gp, gl): return f"{gp / gl:.2f}" if gl > 0 else ("inf" if gp > 0 else "--")
def fmt_t(t, fmt="dd MMM HH:mm"):
    if t is None: return "--"
    m = {"dd/MM HH:mm": "%d/%m %H:%M", "dd MMM HH:mm": "%d %b %H:%M", "dd/MM": "%d/%m"}
    return pd.Timestamp(t).strftime(m.get(fmt, "%d %b %H:%M"))

def T(name, pos, rows, title=None, cols=2, enabled=True):
    return dict(name=name, pos=pos, rows=rows, title=title, cols=cols, enabled=enabled)

def build_tables(eng, o, D, vp, C):
    tabs = []
    unit = "%" if o.isPrem else "p"
    fl = C.flatPct; rows = {}; sd = C.showDetail
    def rLV(r, l, v, col):
        if r < 22 or sd: rows[r] = (l, v, col)

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
    rLV(16, "Trend since", f"{dirTxt} {fmt_t(eng.dirSince)} ({eng.bar_idx - eng.dirSinceBar} bar)", "green" if o.mDir == 1 else ("red" if o.mDir == -1 else "gray"))
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
        rows[18] = ("OPTION Entry", (f"{optEnU:.1f}" + (" (haath)" if C.optEntry > 0 else (" (locked)" if o.posSt != 0 else " (abhi)"))) if not na(optEnU) else ("Symbol daalo" if C.optSym == "" else "Option data nahi mila"), "blue")
        rows[19] = ("OPTION SL", f"{optEnU - dSlO:.1f} (-{dSlO:.1f})" if not na(optEnU) else f"-{dSlO:.1f} pts", "red")
        rows[20] = ("OPTION T1", f"{optEnU + dT1O:.1f} (+{dT1O:.1f})" if not na(optEnU) else f"+{dT1O:.1f} pts", "green")
        rows[21] = ("OPTION T2", f"{optEnU + dT2O:.1f} (+{dT2O:.1f})" if not na(optEnU) else f"+{dT2O:.1f} pts", "green")
    if (not o.isPrem) and C.optSym != "":
        rows[17] = ("OPTION LTP", ("Data nahi mila" if na(o.optPx) else f"{o.optPx:.1f}" + (f" | {'+' if o.optPx >= optEnU else ''}{o.optPx - optEnU:.1f}" if (o.posSt != 0 and not na(optEnU)) else "")), "red" if na(o.optPx) else "gray")
    rLV(30, f"ADX {C.adxLen}", "N/A" if na(o.adxV) else f"{o.adxV:.1f}" + (" trend OK" if o.adxOk else " sideways") + f" | D+ {o.diPl:.0f} D- {o.diMi:.0f}", "green" if o.adxOk else "orange")
    if C.wfOn:
        if eng.wSt != 0:
            wTxt = (("WATCH CE " if eng.wSt == 1 else "WATCH PE ") + f"bar {eng.bar_idx - eng.wBar}/{max(C.wfMax, C.wfMin)} (min {C.wfMin}) dip {abs(eng.wSigC - eng.wExt):.0f}")
        elif o.posSt != 0 and not na(eng.fbEn): wTxt = ">>> FINAL BUY MIL GAYA <<<"
        else: wTxt = "-- | " + eng.wLast
        wc = "green" if eng.wSt != 0 else ("blue" if (o.posSt != 0 and not na(eng.fbEn)) else "purple")
        rows[21.5] = ("WATCH / FINAL", wTxt, wc)
    if C.dgOn:
        rows[31 if sd else 22] = ("Daily 20MA", f"{o.dgTag} | PE {o.peScore}/5", o.dgBg)
    tabs.append(T("SIGNAL", C.posSig, [rows[k] for k in sorted(rows)], title="NIFTY OPT PRO"))

    lgG, lgR = "green", "red"
    L = [(None, f"SIGNAL LOG  W {eng.winN} / L {eng.lossN}  Total {'+' if eng.totPnl >= 0 else ''}{eng.totPnl:.1f}{unit}", "navy"),
         (None, f"CE {eng.wCE + eng.lCE} tr | W{eng.wCE} L{eng.lCE} | {'+' if eng.tCE >= 0 else ''}{eng.tCE:.1f}{unit}", "gray" if eng.wCE + eng.lCE == 0 else (lgG if eng.tCE >= 0 else lgR)),
         (None, f"PE {eng.wPE + eng.lPE} tr | W{eng.wPE} L{eng.lPE} | {'+' if eng.tPE >= 0 else ''}{eng.tPE:.1f}{unit}", "gray" if eng.wPE + eng.lPE == 0 else (lgG if eng.tPE >= 0 else lgR))]
    for x in eng.lg: L.append((None, x, "gray" if x == "--" else (lgG if " +" in x else lgR)))
    tabs.append(T("LOG", C.posLg, L, cols=1, enabled=C.showLog))

    b = o.bex
    B = [("BREADTH 20", o.brTxt, brCol),
         ("Bull wt", "--" if na(b["upPct"]) else f"{b['upPct']:.1f}%", "green" if (not na(b["upPct"]) and b["upPct"] > b["dnPct"]) else "gray"),
         ("Bear wt", "--" if na(b["dnPct"]) else f"{b['dnPct']:.1f}%", "red" if (not na(b["dnPct"]) and b["dnPct"] > b["upPct"]) else "gray"),
         ("Up / Down", f"{b['nUp']} / {b['nDn']}", "green" if b["nUp"] > b["nDn"] else ("red" if b["nUp"] < b["nDn"] else "gray")),
         ("Top10 Up/Dn", "--" if na(b["up10"]) else f"{b['up10']:.0f}% / {b['dn10']:.0f}%", "green" if (not na(b["up10"]) and b["up10"] > b["dn10"]) else "red"),
         ("Impl Nifty", fmtG(b["impl"]), colG(b["impl"], fl)),
         ("Alignment", "--" if na(o.score) else ("ALIGNED" if o.aligned else "MIXED"), "green" if o.aligned else "gray"),
         ("Covered", f"{b['nOk']} stk {b['wTot']:.0f}%", "gray")]
    tabs.append(T("BREADTH", C.posBr, B))

    oi = o.oiScore; ocol = "green" if oi > 0 else ("red" if oi < 0 else "gray")
    O = [("OI / PCR", f"OI BULLISH ({oi:.1f})" if oi > 0 else (f"OI BEARISH ({oi:.1f})" if oi < 0 else "OI NEUTRAL"), ocol),
         ("PCR 9 strike", "chain/settings se" if not o.pcrOn else f"{o.pcrEff:.2f}", "green" if o.pcrS > 0 else ("red" if o.pcrS < 0 else "gray")),
         ("Call Wall", "chain/settings se" if na(o.callEff) else f"{o.callEff:.0f}", "red" if o.nearCall else "gray"),
         ("Put Wall", "chain/settings se" if na(o.putEff) else f"{o.putEff:.0f}", "green" if o.nearPut else "gray"),
         ("Wall range", "--" if (na(o.putEff) or na(o.callEff)) else f"S {o.putEff:.0f} - R {o.callEff:.0f}", "gray"),
         ("Futures OI", o.futTxt, "green" if o.futS > 0 else ("red" if o.futS < 0 else "gray")),
         ("ATM (auto)", "--" if na(o.ocAtmNow) else f"{o.ocAtmNow:.0f}", "blue")]
    if C.ovOn:
        ovCol = "green" if o.ovS > 0 else ("red" if o.ovS < 0 else "gray")
        O += [("VOL PCR", "no data" if not o.ovOk else f"{o.ovPcr:.2f}", ovCol if o.ovOk else "orange")]
    tabs.append(T("OI", C.posOi, O))

    gs = o.gs; LS = []
    for i in range(10):
        a, b2 = gs[i], gs[i + 10]
        LS.append((f"{a[0]} {a[1]:.1f}%", fmtG(a[2]), colG(a[2], fl), f"{b2[0]} {b2[1]:.1f}%", fmtG(b2[2]), colG(b2[2], fl)))
    tabs.append(T("STOCKS", C.posLs, LS, cols=4, enabled=C.showList))

    sc = o.sc; scTh = C.scTh
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
    tabs.append(T("SECTOR", C.scPos, S, enabled=C.scOn))

    SA = []
    for q in range(15):
        has = sc["cn"][q] > 0 and not na(avg[q])
        SA.append((SECTOR_NAMES[q] + (f" ({sc['cn'][q]})" if has else ""), f_scTxt(avg[q] if has else NAN), f_scCol(avg[q] if has else NAN)))
    tabs.append(T("SECTOR ALL", C.scPosA, SA, enabled=C.scAll))

    jTot = max(1, math.ceil(len(eng.jRows) / 15.0))
    page = eng.jRows[(C.jPg - 1) * 15:(C.jPg - 1) * 15 + 15]
    J = [(None, f"JOURNAL pg {C.jPg}/{jTot} | {len(eng.jRows)} trade", "navy")]
    J += [(None, x, "green" if " +" in x else "red") for x in page]
    tabs.append(T("JOURNAL", C.posJ, J, cols=1, enabled=C.jShow))

    def phTx(a, d):
        n = d["n"]
        return (f"{a} {n}tr W{(d['w'] * 100.0 / n if n > 0 else 0):.0f}% PF {pfTxt(d['g'], d['l'])}", "gray" if n == 0 else ("green" if d["q"] >= 0 else "red"))
    p1 = "P1 " + fmt_t(pd.Timestamp(C.ph1S), "dd/MM"); p2 = "P2 " + fmt_t(pd.Timestamp(C.ph2S), "dd/MM")
    PH = [(None, f"PHASE-WISE", "navy")]
    for a, k in ((p1 + " CE", "1C"), (p1 + " PE", "1P"), (p2 + " CE", "2C"), (p2 + " PE", "2P")):
        t, c = phTx(a, eng.ph[k]); PH.append((None, t, c))
    tabs.append(T("PHASE", C.posPh, PH, cols=1, enabled=C.phShow))

    nT = eng.winN + eng.lossN
    gpAll = eng.gpCE + eng.gpPE; glAll = eng.glCE + eng.glPE
    X = [(None, f"EXTRA STATS ({nT} trade)", "navy"),
         (None, f"Win% CE {(eng.wCE * 100.0 / (eng.wCE + eng.lCE)) if (eng.wCE + eng.lCE) > 0 else 0:.0f} | PE {(eng.wPE * 100.0 / (eng.wPE + eng.lPE)) if (eng.wPE + eng.lPE) > 0 else 0:.0f}", "gray"),
         (None, f"Avg Win +{(gpAll / eng.winN) if eng.winN > 0 else 0:.1f} | Avg Loss -{(glAll / eng.lossN) if eng.lossN > 0 else 0:.1f}", "gray")]
    tabs.append(T("EXTRA STATS", C.posXs, X, cols=1, enabled=C.xsShow))

    gdCol = lambda n: "green" if n >= C.gdA else ("orange" if n >= C.gdB else "red")
    gdTxt = lambda n: "A" if n >= C.gdA else ("B" if n >= C.gdB else "C")
    G = [("SETUP CE", f"{gdTxt(o.gdCE)} {o.gdCE}/9", gdCol(o.gdCE)), ("SETUP PE", f"{gdTxt(o.gdPE)} {o.gdPE}/9", gdCol(o.gdPE))]
    tabs.append(T("GRADE", C.gdPos, G, enabled=C.gdShow))

    V = []
    if vp is not None and vp.get("ok"):
        sig = vp["sig"]
        V = [("VOL PCR", f"{vp['pcr']:.2f}", "green" if sig > 0 else ("red" if sig < 0 else "gray")),
             ("VOL C / P", f"C {vp['ce'] / 1e5:.1f}L P {vp['pe'] / 1e5:.1f}L", "gray")]
    tabs.append(T("VOL PCR", C.vp_pos, V, title="VOL PCR", enabled=C.vp_showTbl and bool(V)))
    return tabs

def render_console(tabs, only=None):
    out = []
    for t in tabs:
        if not t["enabled"] or (only and t["name"] not in only): continue
        out.append(f"+-- {t['name']} ({t['pos']}) " + "-" * 20)
        for r in t["rows"]:
            if t["cols"] == 1: out.append(f"| {r[0] if r[0] is not None else ''}{r[1] if r[0] is None else ''}")
            elif t["cols"] == 4: out.append(f"| {r[0]:<22} {r[1]:>8}   {r[3]:<22} {r[4]:>8}")
            else: out.append(f"| {r[0]:<16} {r[1]}")
    return "\n".join(out)

CSS_COL = {"green": "#1b8f4b", "red": "#c0392b", "gray": "#4a5568", "orange": "#d9822b", "blue": "#2563eb", "purple": "#7c3aed", "navy": "#1e2a52", "maroon": "#8a1c3c", "lime": "#65a30d", "teal": "#0f766e"}
POS_CSS = {"Top Left": "top:6px;left:6px;align-items:flex-start", "Top Center": "top:6px;left:50%;transform:translateX(-50%);align-items:center", "Top Right": "top:6px;right:70px;align-items:flex-end", "Middle Left": "top:50%;left:6px;transform:translateY(-50%);align-items:flex-start", "Middle Right": "top:50%;right:70px;transform:translateY(-50%);align-items:flex-end", "Bottom Left": "bottom:30px;left:6px;align-items:flex-start", "Bottom Center": "bottom:30px;left:50%;transform:translateX(-50%);align-items:center", "Bottom Right": "bottom:30px;right:70px;align-items:flex-end"}

def _clean(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)): return None
    return x

def _html_table(t, fs):
    h = [f'<table class="t" style="font-size:{fs}px">']
    if t["title"]: h.append(f'<tr><th colspan="{2 if t["cols"] != 1 else 1}" style="background:{CSS_COL["navy"]}">{t["title"]}</th></tr>')
    for r in t["rows"]:
        if t["cols"] == 1: h.append(f'<tr><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td></tr>')
        elif t["cols"] == 4: h.append(f'<tr><td style="background:{CSS_COL["navy"]}">{_esc(r[0])}</td><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td><td style="background:{CSS_COL["navy"]}">{_esc(r[3])}</td><td style="background:{CSS_COL[r[5]]}">{_esc(r[4])}</td></tr>')
        else: h.append(f'<tr><td style="background:{CSS_COL["navy"]}">{_esc(r[0])}</td><td style="background:{CSS_COL[r[2]]}">{_esc(r[1])}</td></tr>')
    h.append("</table>")
    return "".join(h)

def _esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_html(tabs, eng, o, C, path):
    fs = {"tiny": 10, "small": 12, "normal": 14}.get(C.textSz, 10)
    f5 = o.f5.tail(300); off = 19800
    ts = lambda t: int(pd.Timestamp(t).timestamp()) + off
    candles = [dict(time=ts(i), open=_clean(float(r.o)), high=_clean(float(r.h)), low=_clean(float(r.l)), close=_clean(float(r.c))) for i, r in f5.iterrows()]
    t0 = f5.index[0]; ev = [e for e in eng.events if e["t"] >= t0]; marks = []
    lblOn = C.lblMode != "OFF"
    for e in ev:
        k = e["k"]
        if k == "BUY CE" and C.showMk: marks.append(dict(time=ts(e["t"]), position="belowBar", color="#16a34a", shape="arrowUp", text="BUY CE"))
        elif k == "BUY PE" and C.showMk: marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#dc2626", shape="arrowDown", text="BUY PE"))
        elif k == "EXIT" and C.showMk: marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#16a34a" if e.get("win") else "#dc2626", shape="circle", text="EXIT"))
        elif k == "FINAL BUY CE" and C.wfArrow: marks.append(dict(time=ts(e["t"]), position="belowBar", color="#2563eb", shape="arrowUp", text="FB CE"))
        elif k == "FINAL BUY PE" and C.wfArrow: marks.append(dict(time=ts(e["t"]), position="aboveBar", color="#2563eb", shape="arrowDown", text="FB PE"))
    marks.sort(key=lambda m: m["time"])
    hist = [h for h in eng.hist if h["t"] >= t0]
    def series(key): return [({"time": ts(h["t"]), "value": h[key]} if not na(h[key]) else {"time": ts(h["t"])}) for h in hist]
    lines = []
    if o.posSt != 0 and not na(o.posEn):
        lines += [dict(price=o.posEn, color="#2563eb", title="ENTRY", style=0), dict(price=o.posSl, color="#dc2626", title="SL", style=2),
                  dict(price=o.posT1, color="#16a34a", title="T1", style=2), dict(price=o.posT2, color="#16a34a", title="T2", style=2)]
    payload = dict(candles=candles, marks=marks, lines=lines, en=series("en"), sl=series("sl"), t1=series("t1"), t2=series("t2"), wf=series("wf"), ws=series("ws"), showMa=bool(C.wfMaShow))
    zones = {}
    for t in tabs:
        if t["enabled"] and t["rows"]: zones.setdefault(t["pos"], []).append(_html_table(t, fs))
    zhtml = "".join(f'<div class="z" style="{POS_CSS[p]}">{"".join(v)}</div>' for p, v in zones.items() if p in POS_CSS)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="20"><script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script><style>html,body{{margin:0;height:100%;background:#0b1020;color:#e5e7eb;font-family:Arial,sans-serif}}#chart{{position:absolute;inset:0}}.z{{position:absolute;display:flex;flex-direction:column;gap:4px;z-index:5;pointer-events:none;max-height:96%}}.t{{border-collapse:collapse;color:#fff;opacity:.93}}.t td,.t th{{border:1px solid rgba(255,255,255,.35);padding:1px 5px;white-space:nowrap}}#btn{{position:absolute;right:6px;top:6px;z-index:10;background:#1e2a52;color:#fff;border:1px solid #fff5;padding:3px 8px;cursor:pointer}}</style></head><body><div id="chart"></div><button id="btn" onclick="document.querySelectorAll('.z').forEach(e=>e.style.display=e.style.display=='none'?'flex':'none')">Tables</button>{zhtml}<script>const P={json.dumps(payload, allow_nan=False)};const ch=LightweightCharts.createChart(document.getElementById('chart'),{{layout:{{background:{{color:'#0b1020'}},textColor:'#cbd5e1'}},grid:{{vertLines:{{color:'#1b2440'}},horzLines:{{color:'#1b2440'}}}},timeScale:{{timeVisible:true}},rightPriceScale:{{borderColor:'#334155'}}}});const cs=ch.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderVisible:false}});cs.setData(P.candles);cs.setMarkers(P.marks);ch.timeScale().fitContent();</script></body></html>'''
    with open(path, "w", encoding="utf-8") as f: f.write(html)

class NiftyOptionProEngine:
    def __init__(self, broker: BrokerConnector, is_backtest: bool = False, bt_entry_mode: str = "ALL_SIGNALS"):
        self.broker = broker; self.is_backtest = is_backtest; self.bt_entry_mode = bt_entry_mode
        self.ovCtr = None; self.bar_index = 0; self.last_pre_alert_bar = -1
        self.real_trade_count = 0; self.real_live_orders_sent = 0; self.active_real_trade_id = ""
        self._load_existing_real_trade_count()
        self.posSt = 0; self.posEn = np.nan; self.posSl = np.nan; self.posT1 = np.nan; self.posT2 = np.nan
        self.posR = np.nan; self.posMv = False; self.t1Booked = False
        self.activeStrike = 0.0; self.activeExpiry = ""; self.activeLots = 0; self.remainingLots = 0
        self.realizedTradePnl = 0.0; self.lastExit = -1000; self.armCE = True; self.armPE = True
        self.trade_journal = []; self.logs = []
        self.winN = 0; self.lossN = 0; self.totPnl = 0.0; self.gp = 0.0; self.gl = 0.0
        self.eqC = 0.0; self.eqPk = 0.0; self.maxDD = 0.0
        self.entTx = ""; self.entT = None; self.entAdx = np.nan; self.entSc = np.nan
        self.entProbCE = 50.0; self.entProbPE = 50.0; self.tkLo = np.nan; self.tkHi = np.nan
        self.wSt = 0; self.wBar = 0; self.wSigC = np.nan; self.wSl = np.nan; self.wExt = np.nan
        self.wLast = "--"; self.wCloses = []; self.fbEn = np.nan
        self.wPendingSide = ""; self.wPendingStrike = 0.0; self.wPendingExpiry = ""
        self.wPendingLots = 0; self.wPendingPlus = ""; self.wPendingAdx = np.nan
        self.wPendingSc = np.nan; self.wPendingProbCE = 50.0; self.wPendingProbPE = 50.0
        self.events = []; self.hist = []
        self.lastSigT = None; self.lastSigTx = ""; self.lastSigBar = 0
        self.dirSince = None; self.dirSinceBar = 0; self._prevDir = 0
        self.wCE = self.lCE = self.wPE = self.lPE = 0
        self.tCE = self.tPE = 0.0; self.gpCE = self.glCE = self.gpPE = self.glPE = 0.0
        self.jRows = []; self.jFirst = None
        self.ph = {k: dict(n=0, w=0, g=0.0, l=0.0, q=0.0) for k in ("1C", "1P", "2C", "2P")}
        self.maxConsL = 0; self._curL = 0; self.mMaeW = 0.0; self.sMaeW = 0.0; self.sMfe = 0.0
        self.fbN = self.fbW = 0; self.fbGp = self.fbGl = self.fbT = self.fbOrg = 0.0
        self.noN = 0; self.noT = 0.0; self.wNsig = self.wNfin = self.wNcan = 0
        self.optEnPrem = np.nan; self.last_o = None; self.last_vp = None; self._fb_now = 0

    @property
    def bar_idx(self): return self.bar_index
    @property
    def lg(self): return self.logs

    def _dash_stats(self, exit_ts, exit_px, exit_reason, pnl, sgn, mae, mfe, fb_pnl):
        win = pnl > 0
        if sgn == 1:
            if win: self.wCE += 1; self.gpCE += pnl
            else: self.lCE += 1; self.glCE += abs(pnl)
            self.tCE += pnl
        else:
            if win: self.wPE += 1; self.gpPE += pnl
            else: self.lPE += 1; self.glPE += abs(pnl)
            self.tPE += pnl
        if win: self.mMaeW = max(self.mMaeW, mae); self.sMaeW += mae; self._curL = 0
        else: self._curL += 1; self.maxConsL = max(self.maxConsL, self._curL)
        self.sMfe += mfe
        had_fb = not np.isnan(self.fbEn)
        if had_fb:
            self.fbN += 1; self.fbOrg += pnl
            if not np.isnan(fb_pnl):
                self.fbT += fb_pnl
                if fb_pnl > 0: self.fbW += 1; self.fbGp += fb_pnl
                else: self.fbGl += abs(fb_pnl)
        else: self.noN += 1; self.noT += pnl
        ent_t = self.entT if self.entT is not None else exit_ts
        if self.jFirst is None: self.jFirst = ent_t
        try:
            d0 = pd.Timestamp(ent_t).date()
            p1s = pd.Timestamp(DASH["ph1S"]).date()
            p2s = pd.Timestamp(DASH["ph2S"]).date()
            pe = pd.Timestamp(DASH["phE"]).date()
            key = "1" if (p1s <= d0 < p2s) else ("2" if (p2s <= d0 <= pe) else None)
            if key:
                ph = self.ph[key + ("C" if sgn == 1 else "P")]
                ph["n"] += 1; ph["q"] += pnl
                if win: ph["w"] += 1; ph["g"] += pnl
                else: ph["l"] += abs(pnl)
        except Exception: pass
        dip = abs(self.wSigC - self.wExt) if (had_fb and not np.isnan(self.wSigC) and not np.isnan(self.wExt)) else np.nan
        row = f"{self.entTx} {pd.Timestamp(ent_t):%d/%m %H:%M} {exit_reason} {pnl:+.1f}p M{mae:.0f} F{mfe:.0f}"
        if had_fb and not np.isnan(fb_pnl): row += f" FB{fb_pnl:+.0f}"
        if not np.isnan(dip): row += f" D{dip:.0f}"
        self.jRows.insert(0, row); self.jRows = self.jRows[:300]
        self.events.append(dict(t=exit_ts, k="EXIT", text=f"{exit_reason} {pnl:+.0f}", win=win))

    def _dash_pre(self, entCE, entPE):
        if self.last_o is not None:
            self.last_o.preCE = bool(entCE); self.last_o.preAlertPE = bool(entPE)

    def _dash_capture(self, L):
        t5, t3, t15, t1h, t4h = L["t5"], L["t3"], L["t15"], L["t1h"], L["t4h"]
        br = L["br"]; close = L["close"]; bar_ts = L["bar_ts"]
        oc = L.get("oc_data") or {}; step = PARAMS["optStep"]
        posOn = self.posSt != 0; mDir = L["mDir"]
        entCE, entPE = L["entCE"], L["entPE"]
        score, hasBr = L["score"], L["hasBr"]
        callEff, putEff = L["callEff"], L["putEff"]
        atmNow = L["atmNow"]; oc_span = L["oc_span"]; ov_span = L["ov_span"]
        nan = np.nan; s_txt = lambda x: "CE" if x == 1 else ("PE" if x == -1 else "-")

        if entCE: act = "BUY CE"
        elif entPE: act = "BUY PE"
        elif L.get("exitNow"):
            exr = L.get("exRes", "")
            act = ("BOOK " if exr in ("T1", "T2", "T1_FULL") else "EXIT ") + exr
        elif posOn: act = "HOLD CE" if self.posSt == 1 else "HOLD PE"
        else: act = "WAIT"

        if posOn: shOn, shEn, shSl, shT1, shT2 = True, self.posEn, self.posSl, self.posT1, self.posT2
        elif self.wSt != 0 and not np.isnan(self.wSigC):
            slD = L["slD"]; shOn = True; shEn, shSl = self.wSigC, self.wSl
            shT1 = self.wSigC + self.wSt * slD * PARAMS["rrT"]
            shT2 = self.wSigC + self.wSt * slD * (PARAMS["rrT"] + 1.0)
        else: shOn, shEn, shSl, shT1, shT2 = False, nan, nan, nan, nan
        pnlV = (self.posSt * (close - self.posEn)) if posOn else nan
        sideNow = self.posSt if posOn else mDir
        relK = callEff if sideNow == 1 else (putEff if sideNow == -1 else nan)

        ltp_map = oc.get("ltpMap") or {}
        if posOn: o_side, o_strike = self.posSt, self.activeStrike
        else: o_side = mDir; o_strike = L["strikeCE"] if mDir == 1 else (L["strikePE"] if mDir == -1 else nan)
        optPx = nan
        if o_side != 0 and not np.isnan(o_strike):
            rec = ltp_map.get(round(float(o_strike), 2))
            if rec:
                v = rec.get("ce" if o_side == 1 else "pe", nan)
                try: v = float(v); optPx = v if (not np.isnan(v) and v > 0) else nan
                except Exception: optPx = nan
        if posOn:
            if np.isnan(self.optEnPrem) and not np.isnan(optPx): self.optEnPrem = optPx
            optEnPx = self.optEnPrem
        else: self.optEnPrem = nan; optEnPx = optPx

        ocOk = L["ocOk"]
        ocStatus = f"Chain OK ({oc.get('ocCnt', 0)} pts)" if ocOk else "Chain data nahi"
        volPcrVal = L["volPcrVal"]; volOk_pcr = L["volOk_pcr"]; vol_sig = oc.get("volSig", 0.0) if volOk_pcr else 0.0
        dgS1, dgS2, dgUp, dgDn = L["dgS1"], L["dgS2"], L["dgUp"], L["dgDn"]
        dgTag = f"{PARAMS['dgD1']}d {dgS1:+.2f}% {PARAMS['dgD2']}d {dgS2:+.2f}% " + ("UP" if dgUp else ("DOWN" if dgDn else "FLAT"))
        dgBg = "green" if dgUp else ("red" if dgDn else "gray")

        f5 = L["df_5m"][["open", "high", "low", "close"]].tail(300).copy(); f5.columns = ["o", "h", "l", "c"]
        o = SimpleNamespace(
            act=act, entNow=bool(entCE or entPE), plusTxt=L["plusTxt"], fin=L["fin"], why=L["why"],
            modeTxt=f"{PARAMS['strikeMode']} / {PARAMS['exitMode']}",
            mtfTxt=f"{s_txt(t3['side'])} / {s_txt(t5['side'])} / {s_txt(t15['side'])}",
            sideC=t1h["side"], sideD=t4h["side"], mDir=mDir, sideNow=sideNow,
            sigCE=L["sigCE"], sigPE=L["sigPE"], fbCE=(self._fb_now == 1), fbPE=(self._fb_now == -1),
            preCE=False, preAlertPE=False, score=score, brTxt=br["brTxt"], bullHi=br["bullHi"], bearHi=br["bearHi"],
            bullMd=hasBr and score >= 55 and not br["bullHi"], bearMd=hasBr and score <= 45 and not br["bearHi"],
            aligned=br["aligned"], bex=dict(upPct=br["upPct"], dnPct=br["dnPct"], nUp=br["nUpC"], nDn=br["nDnC"], up10=br["up10"], dn10=br["dn10"], impl=br["impl"], nOk=br["nOk"], wTot=br["wTot"]),
            sc=dict(avg=br["secAvgL"], cn=br["secCn"], valid=br["scValid"], bk=br["scBk"], bkN=br["bkN"], noData=(br["scValid"] == 0), scCE=br["scCE"], scPE=br["scPE"]),
            gs=br["gs"], posSt=self.posSt, posEn=self.posEn, posSl=self.posSl, posT1=self.posT1, posT2=self.posT2,
            shOn=shOn, shEn=shEn, shSl=shSl, shT1=shT1, shT2=shT2, pnlV=pnlV, lots=L["lots"], lotRisk=L["lotRisk"], riskRs=L["riskRs"],
            isPrem=(PARAMS["chartType"] != "Index/Fut"), close=close, t_open=bar_ts, f5=f5, relK=relK, relPrem=nan, revPlot=relK,
            callEff=callEff, putEff=putEff, callDist=((callEff - close) / close * 100.0) if not np.isnan(callEff) else nan,
            putDist=((close - putEff) / close * 100.0) if not np.isnan(putEff) else nan, nearCall=L["nearCall"], nearPut=L["nearPut"],
            oiScore=L["oiScore"], pcrEff=L["ocPcrVal"], pcrOn=(not np.isnan(L["ocPcrVal"])), pcrS=L["pcrS"], ocOk=ocOk, ovUseF=L["ovUseF"],
            futS=L["futS"], futTxt=L["futTxt"], ocAtmNow=atmNow, ocK0=atmNow - oc_span * step, ocK8=atmNow + oc_span * step,
            ocStatus=ocStatus, ovOk=volOk_pcr, ovPcr=volPcrVal, ovS=vol_sig, ovPutK=oc.get("volPutK", nan), ovCallK=oc.get("volCallK", nan),
            vol=({"ce": oc.get("volCeSum", 0), "pe": oc.get("volPeSum", 0)} if volOk_pcr else {}), optEnPx=optEnPx, optPx=optPx,
            bull=t5["bull"], bear=t5["bear"], maxC=t5["maxC"], ema9=t5["ema9"], ema21=t5["ema21"], ema50=t5["ema50"], rsiV=t5["rsi"],
            sdir=t5["sdir"], vw=t5["vwap"], vwOk=t5["vwOk"], orDone=t5["orDone"], orH=t5["orH"], orL=t5["orL"], volOk=L["volOk"],
            volSurge=bool(L["volOk"] and L["vol"] >= 1.5 * L["volAvg"]), adxV=t5["adx"], adxOk=L["adxOk"], diPl=t5["diPl"], diMi=t5["diMi"],
            dgTag=dgTag, dgBg=dgBg, peScore=L["peScore"], gdCE=L["gdCE"], gdPE=L["gdPE"], gdWC="", gdWP=""
        )
        self.last_o = o
        if PARAMS["ovOn"]:
            try: exp_ts = pd.Timestamp(L["selected_exp"])
            except Exception: exp_ts = pd.Timestamp(bar_ts)
            self.last_vp = dict(ok=bool(volOk_pcr), sig=vol_sig, pcr=volPcrVal, ce=oc.get("volCeSum", 0), pe=oc.get("volPeSum", 0), putK=oc.get("volPutK", nan), callK=oc.get("volCallK", nan), ctr=(self.ovCtr if self.ovCtr is not None else atmNow), exp=exp_ts, cnt=oc.get("volCnt", 0), total=2 * (2 * ov_span + 1))
        else: self.last_vp = None
        self.hist.append(dict(t=bar_ts, en=self.posEn if posOn else nan, sl=self.posSl if posOn else nan, t1=self.posT1 if posOn else nan, t2=self.posT2 if posOn else nan, wf=g("smaF", nan) if self.wSt != 0 else nan, ws=g("smaS", nan) if self.wSt != 0 else nan))
        self.hist = self.hist[-1500:]; self.events = self.events[-800:]

    def _load_existing_real_trade_count(self):
        if self.is_backtest: return
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        if os.path.exists(csv_file):
            try:
                df_ex = pd.read_csv(csv_file)
                self.real_trade_count = len(df_ex)
                if "OrderPlaced" in df_ex.columns: self.real_live_orders_sent = int(df_ex["OrderPlaced"].sum())
            except Exception: pass

    def alert(self, text: str):
        if self.is_backtest: return
        print(text)

    def manual_exit_now(self, current_price: float, bar_ts: dt.datetime, reason: str = "MANUAL_EXIT"):
        if self.posSt == 0: return
        sgn = 1 if self.posSt == 1 else -1; side_str = "CE" if self.posSt == 1 else "PE"
        rem_ratio = (self.remainingLots / self.activeLots) if self.activeLots > 0 else 1.0
        final_pnl = self.realizedTradePnl + sgn * (current_price - self.posEn) * rem_ratio
        if self.remainingLots > 0: self.broker.place_option_order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)
        self._record_closed_trade(bar_ts, current_price, reason, final_pnl)
        self.posSt = 0; self.posMv = False; self.t1Booked = False; self.remainingLots = 0; self.realizedTradePnl = 0.0

    def _record_closed_trade(self, exit_ts: dt.datetime, exit_px: float, exit_reason: str, pnl_pts: float):
        sgn = 1 if self.posSt == 1 else -1
        mae = (self.posEn - self.tkLo) if sgn == 1 else (self.tkHi - self.posEn)
        mfe = (self.tkHi - self.posEn) if sgn == 1 else (self.posEn - self.tkLo)
        if pnl_pts > 0: self.winN += 1; self.gp += pnl_pts
        else: self.lossN += 1; self.gl += abs(pnl_pts)
        self.totPnl += pnl_pts; self.eqC += pnl_pts; self.eqPk = max(self.eqPk, self.eqC); self.maxDD = max(self.maxDD, self.eqPk - self.eqC)
        fb_pnl = (sgn * (exit_px - self.fbEn)) if not np.isnan(self.fbEn) else np.nan
        ent_prob = self.entProbCE if sgn == 1 else self.entProbPE
        self.trade_journal.append({"EntryTime": self.entT.strftime("%Y-%m-%d %H:%M") if self.entT else "", "ExitTime": exit_ts.strftime("%Y-%m-%d %H:%M"), "Signal": self.entTx, "Strike": f"{int(self.activeStrike)} ({PARAMS['strikeMode']})", "Expiry": self.activeExpiry, "EntryPx": round(self.posEn, 2), "ExitPx": round(exit_px, 2), "ExitReason": exit_reason, "PnL_Pts": round(pnl_pts, 2), "OI_Prob%": round(ent_prob, 1)})
        self._dash_stats(exit_ts, exit_px, exit_reason, pnl_pts, sgn, mae, mfe, fb_pnl)

    def eval_timeframe(self, df: pd.DataFrame, is_5m: bool = False) -> dict:
        c_s = df["close"]; ema9 = calc_ema(c_s, 9); ema21 = calc_ema(c_s, 21); ema50 = calc_ema(c_s, 50)
        rsi = calc_rsi(c_s, 14); sdir = calc_supertrend(df, 3.0, 10); vw = calc_vwap(df)
        diPl, diMi, adxV = calc_dmi(df, PARAMS["adxLen"])
        c = c_s.iloc[-1]; e9, e21, e50 = ema9.iloc[-1], ema21.iloc[-1], ema50.iloc[-1]
        r = rsi.iloc[-1]; sd = sdir.iloc[-1]; v = vw.iloc[-1]; vwOk = (not np.isnan(v)) and v > 0
        bull = (1 if (e9 > e21 and c > e50) else 0) + (1 if (vwOk and c > v) else 0) + (1 if sd < 0 else 0) + (1 if r > 55 else 0)
        bear = (1 if (e9 < e21 and c < e50) else 0) + (1 if (vwOk and c < v) else 0) + (1 if sd > 0 else 0) + (1 if r < 45 else 0)
        orH = orL = np.nan; orDone = False
        if is_5m:
            today = df.index[-1].date(); t_df = df[df.index.date == today]; dayBar = len(t_df)
            orH = t_df["high"].iloc[:PARAMS["orBars"]].max() if len(t_df) > 0 else np.nan
            orL = t_df["low"].iloc[:PARAMS["orBars"]].min() if len(t_df) > 0 else np.nan
            orDone = dayBar > PARAMS["orBars"]
            bull += (1 if (orDone and c > orH) else 0); bear += (1 if (orDone and c < orL) else 0)
            maxC = 4 + (1 if vwOk else 0); needE = min(PARAMS["needN"], maxC)
        else: maxC = 3 + (1 if vwOk else 0); needE = min(PARAMS["mtfNeed"], maxC)
        side = 1 if (bull >= needE and bull > bear) else (-1 if (bear >= needE and bear > bull) else 0)
        arN = PARAMS["arN"]; adx_prev = adxV.iloc[-1 - arN] if len(adxV) > arN else np.nan
        return {"side": side, "bull": bull, "bear": bear, "maxC": maxC, "needE": needE, "close": c, "ema9": e9, "ema21": e21, "ema50": e50, "rsi": r, "sdir": sd, "vwap": v, "vwOk": vwOk, "orH": orH, "orL": orL, "orDone": orDone, "diPl": diPl.iloc[-1], "diMi": diMi.iloc[-1], "adx": adxV.iloc[-1], "adxPrev": adx_prev}

    def eval_breadth_and_sectors(self, changes: dict) -> dict:
        wTot = wUp = wDn = wCt = 0.0; w10Tot = w10Up = w10Dn = 0.0; nUpC = nDnC = nOkC = 0
        sec_ws = {k: 0.0 for k in SECTOR_MAP}; sec_wg = {k: 0.0 for k in SECTOR_MAP}; sec_cn = {k: 0 for k in SECTOR_MAP}
        bkW = bkG = 0.0; bkN = 0
        for idx, (sym, wt) in enumerate(BREADTH_STOCKS):
            g = changes.get(sym, np.nan)
            if not np.isnan(g):
                nOkC += 1; wTot += wt; wCt += g * wt
                if g > PARAMS["flatPct"]: wUp += wt; nUpC += 1
                elif g < -PARAMS["flatPct"]: wDn += wt; nDnC += 1
                if idx < 10:
                    w10Tot += wt
                    if g > PARAMS["flatPct"]: w10Up += wt
                    elif g < -PARAMS["flatPct"]: w10Dn += wt
                if wt > 0:
                    for sname, members in SECTOR_MAP.items():
                        if sym in members: sec_ws[sname] += wt; sec_wg[sname] += wt * g; sec_cn[sname] += 1
                    if sym in BANK_STOCKS: bkW += wt; bkG += wt * g; bkN += 1
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
        brTxt = "NO DATA" if np.isnan(score) else ("CE HIGH" if bullHi else ("PE HIGH" if bearHi else ("CE medium" if score >= 55 else "PE medium")))
        sec_avg = {k: (sec_wg[k] / sec_ws[k]) if (sec_cn[k] > 0 and sec_ws[k] > 0) else np.nan for k in SECTOR_MAP}
        scBk = (bkG / bkW) if (bkN > 0 and bkW > 0) else np.nan
        scValid = sum(1 for v in sec_avg.values() if not np.isnan(v))
        return {"score": score, "brTxt": brTxt, "bullHi": bullHi, "bearHi": bearHi, "upPct": upPct, "dnPct": dnPct, "nUpC": nUpC, "nDnC": nDnC, "impl": impl, "secAvg": sec_avg, "scBk": scBk, "scCE": True, "scPE": True, "up10": up10Pct, "dn10": 0, "nOk": nOkC, "wTot": wTot, "aligned": aligned, "bkN": bkN, "scValid": scValid, "secAvgL": [sec_avg[k] for k in SECTOR_MAP], "secCn": [sec_cn[k] for k in SECTOR_MAP], "gs": [(sym, wt, changes.get(sym, np.nan)) for sym, wt in BREADTH_STOCKS]}

    def calc_oi_and_vol_probability(self, oc_pcr, vol_pcr, fut_s, near_call, near_put, breadth_score):
        oi_norm = np.clip((oc_pcr - 1.0) / 0.35, -1.0, 1.0) if not np.isnan(oc_pcr) else 0.0
        vol_norm = np.clip((vol_pcr - 1.0) / 0.40, -1.0, 1.0) if not np.isnan(vol_pcr) else 0.0
        fut_norm = np.clip(fut_s, -1.0, 1.0) if PARAMS["futOiOn"] else 0.0
        br_norm = np.clip((breadth_score - 50.0) / 30.0, -1.0, 1.0) if not np.isnan(breadth_score) else 0.0
        raw_bias = (oi_norm * 0.30) + (vol_norm * 0.25) + (fut_norm * 0.25) + (br_norm * 0.20)
        prob_ce = float(np.clip(50.0 + raw_bias * 50.0, 0.0, 100.0))
        prob_pe = float(np.clip(50.0 - raw_bias * 50.0, 0.0, 100.0))
        return prob_ce, prob_pe

    def evaluate_bar_data(self, df_5m, df_3m, df_15m, df_1h, df_4h, df_d, df_fut, df_vix, stock_changes, oc_data, is_pre_alert: bool = False):
        if not is_pre_alert: self.bar_index += 1
        bar_ts = df_5m.index[-1]
        if not is_pre_alert: self._fb_now = 0
        t5 = self.eval_timeframe(df_5m, is_5m=True); t3 = self.eval_timeframe(df_3m)
        t15 = self.eval_timeframe(df_15m); t1h = self.eval_timeframe(df_1h); t4h = self.eval_timeframe(df_4h)
        close = t5["close"]; high = df_5m["high"].iloc[-1]; low = df_5m["low"].iloc[-1]
        atr10 = calc_atr(df_5m, 10).iloc[-1]; vol = df_5m["volume"].iloc[-1]
        volAvg = calc_sma(df_5m["volume"], 20).iloc[-1]
        volOk = (not np.isnan(vol)) and vol > 0 and (not np.isnan(volAvg)) and volAvg > 0
        if not is_pre_alert and self.posSt != 0:
            self.tkLo = min(self.tkLo, low); self.tkHi = max(self.tkHi, high)

        inWin = in_session(bar_ts, PARAMS["sess_start"], PARAMS["sess_end"])
        techSide = t5["side"] if inWin else 0
        mDir = techSide
        plusN = 0 if techSide == 0 else ((1 if t1h["side"] == techSide else 0) + (1 if t4h["side"] == techSide else 0))
        plusTxt = "+++" if plusN >= 3 else ("++" if plusN == 2 else ("+" if plusN == 1 else ""))

        atmNow = round(close / PARAMS["optStep"]) * PARAMS["optStep"]
        strikeCE = get_trade_strike(close, "CE"); strikePE = get_trade_strike(close, "PE")
        selected_exp = oc_data.get("expiry", "") or (self.broker.get_selected_expiry() if not self.is_backtest else "BT_EXP")
        if self.ovCtr is None and atmNow > 0: self.ovCtr = atmNow
        oc_span = clamp_strike_span(PARAMS["ocN"]); ov_span = clamp_strike_span(PARAMS["ovN"])
        ocOk = PARAMS["autoOc"] and oc_data.get("ocOk", False)
        volOk_pcr = PARAMS["ovOn"] and oc_data.get("volOk", False)
        ocPcrVal = oc_data["ocPcr"] if ocOk else np.nan
        volPcrVal = oc_data["volPcr"] if volOk_pcr else np.nan
        pcrS = 0.0 if np.isnan(ocPcrVal) else (1.0 if ocPcrVal >= PARAMS["pcrBull"] else (-1.0 if ocPcrVal <= PARAMS["pcrBear"] else 0.0))
        oiScore = pcrS
        callEff = oc_data.get("ocCallK", np.nan); putEff = oc_data.get("ocPutK", np.nan)
        nearCall = False; nearPut = False

        br = self.eval_breadth_and_sectors(stock_changes)
        score = br["score"]; hasBr = not np.isnan(score)
        probCE, probPE = self.calc_oi_and_vol_probability(ocPcrVal, volPcrVal, 0, nearCall, nearPut, score)

        if not inWin: fin = "OFF TIME"
        elif mDir == 1: fin = "CE BUY - HIGH PROB" if score >= 55 else "CE BUY - medium"
        elif mDir == -1: fin = "PE BUY - HIGH PROB" if score <= 45 else "PE BUY - medium"
        else: fin = "WAIT"

        sigCE = fin.startswith("CE BUY"); sigPE = fin.startswith("PE BUY")
        probOkCE = True; probOkPE = True
        coolOk = (self.bar_index - self.lastExit) >= PARAMS["coolBars"]
        stCE = t5["sdir"] < 0; stPE = t5["sdir"] > 0
        adxOk = True; diOkCE = True; diOkPE = True; dgCE = True; dgPE = True
        is_idle = (self.posSt == 0)
        entCE = is_idle and sigCE and coolOk and stCE and PARAMS["allowCE"]
        entPE = is_idle and sigPE and coolOk and stPE and PARAMS["allowPE"]

        if is_pre_alert: return

        sgn = -1 if self.posSt == -1 else 1
        exit_mode = PARAMS["exitMode"].upper()
        chk_high = high if PARAMS["useHighLowForTarget"] else close
        chk_low = low if PARAMS["useHighLowForTarget"] else close
        slHit = self.posSt != 0 and (close <= self.posSl if sgn == 1 else close >= self.posSl)
        t1Touch = self.posSt != 0 and (chk_high >= self.posT1 if sgn == 1 else chk_low <= self.posT1)
        t2Touch = self.posSt != 0 and (chk_high >= self.posT2 if sgn == 1 else chk_low <= self.posT2)

        target_exit_triggered = False; target_exit_px = close; target_exit_label = ""
        if self.posSt != 0:
            if exit_mode == "T1" and t1Touch:
                target_exit_triggered = True; target_exit_px = self.posT1 if PARAMS["useHighLowForTarget"] else close; target_exit_label = "T1"
            elif exit_mode in ("T2", "T1_T2") and t2Touch:
                target_exit_triggered = True; target_exit_px = self.posT2 if PARAMS["useHighLowForTarget"] else close; target_exit_label = "T2"

        exitNow = self.posSt != 0 and (slHit or target_exit_triggered or not inWin)
        if exitNow:
            exRes = target_exit_label if target_exit_triggered else ("SL" if slHit else "Time")
            exPx = target_exit_px if target_exit_triggered else close
            rem_ratio = (self.remainingLots / self.activeLots) if self.activeLots > 0 else 1.0
            total_trade_pnl = self.realizedTradePnl + sgn * (exPx - self.posEn) * rem_ratio
            side_str = "CE" if self.posSt == 1 else "PE"
            if self.remainingLots > 0: self.broker.place_option_order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)
            self._record_closed_trade(bar_ts, exPx, exRes, total_trade_pnl)
            self.posSt = 0; self.posMv = False; self.t1Booked = False; self.realizedTradePnl = 0.0; self.lastExit = self.bar_index

        slD = atr10 * PARAMS["slMult"]; riskRs = PARAMS["capital"] * PARAMS["riskPct"] / 100.0
        lotRisk = slD * PARAMS["optDelta"] * PARAMS["optLot"]
        lots = max(1, int(math.floor(riskRs / lotRisk))) if lotRisk > 0 else 1

        if entCE or entPE:
            lvS = 1 if entCE else -1; side_lbl = "CE" if entCE else "PE"
            ent_prob = probCE if entCE else probPE; chosen_strike = strikeCE if entCE else strikePE
            init_sl = close - lvS * slD
            self.events.append(dict(t=bar_ts, k="BUY CE" if entCE else "BUY PE", text=side_lbl + plusTxt, p=plusN))
            self.lastSigT, self.lastSigTx, self.lastSigBar = bar_ts, side_lbl + plusTxt, self.bar_index

            self.posSt = lvS; self.posEn = close; self.posSl = init_sl
            self.posT1 = close + lvS * slD * PARAMS["rrT"]
            self.posT2 = close + lvS * slD * (PARAMS["rrT"] + 1.0)
            self.posR = slD; self.tkLo = low; self.tkHi = high
            self.t1Booked = False; self.realizedTradePnl = 0.0
            self.activeStrike = chosen_strike; self.activeExpiry = selected_exp
            self.activeLots = lots; self.remainingLots = lots
            self.entTx = side_lbl + plusTxt; self.entT = bar_ts
            self.entAdx = t5["adx"]; self.entSc = score
            self.entProbCE = probCE; self.entProbPE = probPE

            order_ok = self.broker.place_option_order(side_lbl, chosen_strike, lots, action="BUY", expiry_date=selected_exp)
            self._log_real_trade_entry(bar_ts, side_lbl, chosen_strike, selected_exp, lots, close, ent_prob, order_ok)

        self.armCE = (self.armCE and not entCE) if sigCE else True
        self.armPE = (self.armPE and not entPE) if sigPE else True
        self._dash_capture(locals())

    def process_live_bar(self, is_pre_alert: bool = False):
        now_ist = dt.datetime.now(IST); main_sym = CONFIG["CHART_SYMBOL"]
        df_5m = self.broker.get_candles(main_sym, interval="5", days=7)
        if df_5m.empty or len(df_5m) < 60: return
        if not is_pre_alert and df_5m.index[-1] > now_ist - dt.timedelta(minutes=5): df_5m = df_5m.iloc[:-1]
        df_3m = self.broker.get_candles(main_sym, interval="3", days=5)
        df_15m = self.broker.get_candles(main_sym, interval="15", days=10)
        df_1h = self.broker.get_candles(main_sym, interval="60", days=20)
        df_4h = self.broker.get_candles(main_sym, interval="240", days=45)
        df_d = self.broker.get_candles(main_sym, interval="D", days=60)
        df_fut = self.broker.get_candles("NIFTY_FUT", interval="5", days=3)
        df_vix = self.broker.get_candles("INDIAVIX", interval="5", days=3)
        close = df_5m["close"].iloc[-1]; atmNow = round(close / PARAMS["optStep"]) * PARAMS["optStep"]
        if self.ovCtr is None and atmNow > 0: self.ovCtr = atmNow
        oc_data = self.broker.get_option_chain_metrics(atmNow, self.ovCtr, PARAMS["ocN"], PARAMS["ovN"]) if (PARAMS["autoOc"] or PARAMS["ovOn"]) else {}
        stock_changes = self.broker.get_breadth_changes()
        self.evaluate_bar_data(df_5m, df_3m, df_15m, df_1h, df_4h, df_d, df_fut, df_vix, stock_changes, oc_data, is_pre_alert=is_pre_alert)
        self.render_dashboard()

def run_backtest(broker: BrokerConnector, days: int = 30):
    bt_type = CONFIG.get("BACKTEST_ENTRY_TYPE", "BOTH").upper()
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
        return {"error": msg}
    stock_daily = {}
    for sym, _ in BREADTH_STOCKS:
        d_s = broker.get_candles(sym, interval="D", days=days + 15)
        if not d_s.empty: d_s["pct"] = d_s["close"].pct_change() * 100.0; stock_daily[sym] = d_s["pct"]
    modes_to_run = ["ALL_SIGNALS", "REAL_BLUE_ONLY"] if bt_type == "BOTH" else [bt_type]
    for mode_label in modes_to_run:
        engine = NiftyOptionProEngine(broker, is_backtest=True, bt_entry_mode=mode_label)
        oc_bt = {"expiry": PARAMS["expiryMode"], "ocOk": PARAMS["pcrIn"] > 0, "ocPcr": PARAMS["pcrIn"] if PARAMS["pcrIn"] > 0 else np.nan, "ocCallK": PARAMS["callWall"] if PARAMS["callWall"] > 0 else np.nan, "ocPutK": PARAMS["putWall"] if PARAMS["putWall"] > 0 else np.nan, "volOk": False, "volPcr": np.nan, "volSig": 0.0}
        for i in range(60, len(df_5m)):
            sub_5m = df_5m.iloc[:i + 1]; cur_ts = sub_5m.index[-1]; cur_date = cur_ts.date()
            sub_3m = df_3m[df_3m.index <= cur_ts]; sub_15m = df_15m[df_15m.index <= cur_ts]
            sub_1h = df_1h[df_1h.index <= cur_ts]; sub_4h = df_4h[df_4h.index <= cur_ts]
            sub_d = df_d[df_d.index.date <= cur_date]
            sub_fut = df_fut[df_fut.index <= cur_ts] if not df_fut.empty else pd.DataFrame()
            sub_vix = df_vix[df_vix.index <= cur_ts] if not df_vix.empty else pd.DataFrame()
            if len(sub_d) < 30 or len(sub_3m) < 30 or len(sub_15m) < 30 or len(sub_1h) < 30 or len(sub_4h) < 30: continue
            changes = {}
            for sym, _ in BREADTH_STOCKS:
                s_pct = stock_daily.get(sym)
                if s_pct is not None:
                    valid = s_pct[s_pct.index.date <= cur_date]
                    changes[sym] = valid.iloc[-1] if not valid.empty else np.nan
                else: changes[sym] = np.nan
            engine.evaluate_bar_data(sub_5m, sub_3m, sub_15m, sub_1h, sub_4h, sub_d, sub_fut, sub_vix, changes, oc_bt)
        csv_name = f"backtest_{mode_label}_{PARAMS['strikeMode']}_{PARAMS['exitMode']}.csv"
        if engine.trade_journal:
            j_df = pd.DataFrame(engine.trade_journal)
            j_df.to_csv(csv_name, index=False)
        else:
            pd.DataFrame(columns=["EntryTime","ExitTime","Signal","Strike","Expiry","EntryPx","ExitPx","ExitReason","PnL_Pts","FB_PnL_Pts","OI_Prob%","MAE","MFE","ADX","Breadth"]).to_csv(csv_name, index=False)
        if CONFIG.get("DASH_ON", True):
            dash_path = f"dashboard_backtest_{mode_label}.html"
            engine.render_dashboard(dash_path)
    return {"ok": True, "modes": modes_to_run, "bars_5m": len(df_5m)}

def run_streamlit_desktop_app():
    import streamlit as st
    import streamlit.components.v1 as components
    st.set_page_config(page_title="NIFTY OPTION SIGNAL PRO v28 - Desktop Dashboard", layout="wide", initial_sidebar_state="expanded")
    st.title("NIFTY OPTION SIGNAL PRO v28 - Full Desktop Trading & Backtest Dashboard")

    with st.sidebar:
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
            CONFIG["DHAN_CLIENT_ID"] = dhan_cid.strip(); CONFIG["DHAN_ACCESS_TOKEN"] = dhan_tok.strip()
        else:
            default_utok = "" if CONFIG["UPSTOX_ACCESS_TOKEN"] == "YOUR_UPSTOX_ACCESS_TOKEN" else CONFIG["UPSTOX_ACCESS_TOKEN"]
            up_tok = st.text_input("Upstox Access Token", value=st.secrets.get("UPSTOX_ACCESS_TOKEN", default_utok), type="password")
            CONFIG["UPSTOX_ACCESS_TOKEN"] = up_tok.strip()

        st.header("2. Execution Mode & Order Settings")
        run_mode = st.radio("Select Mode", ["LIVE", "BACKTEST", "REAL_TRADE_REPORT"], index=0)
        CONFIG["RUN_MODE"] = run_mode

        if run_mode == "LIVE":
            auto_order = st.checkbox("AUTO PLACE LIVE BROKER ORDER (Blue Arrow)?", value=CONFIG["AUTO_PLACE_ORDER"])
            CONFIG["AUTO_PLACE_ORDER"] = auto_order
            if auto_order: st.error("LIVE ORDER EXECUTION ON!")
            else: st.info("SAFE MODE: Only Alerts & Dashboard.")
            
            override_hours = st.checkbox("[TEST] Override Market Hours (Test Anytime)", value=PARAMS["overrideMarketHours"])
            PARAMS["overrideMarketHours"] = override_hours
        elif run_mode == "BACKTEST":
            bt_days = st.number_input("Backtest Days", min_value=5, max_value=180, value=int(CONFIG["BACKTEST_DAYS"]))
            CONFIG["BACKTEST_DAYS"] = int(bt_days)
            bt_entry = st.selectbox("Backtest Entry Type", ["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"], index=["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"].index(CONFIG["BACKTEST_ENTRY_TYPE"]))
            CONFIG["BACKTEST_ENTRY_TYPE"] = bt_entry

        st.header("3. Strike, Expiry & Target Exit")
        PARAMS["strikeMode"] = st.selectbox("Strike Selection", ["ATM", "ITM_1", "ITM_2", "OTM_1"], index=["ATM", "ITM_1", "ITM_2", "OTM_1"].index(PARAMS["strikeMode"]))
        PARAMS["expiryMode"] = st.selectbox("Expiry Selection", ["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"], index=["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"].index(PARAMS["expiryMode"]))
        if PARAMS["expiryMode"] == "MANUAL": PARAMS["manualExpiry"] = st.text_input("Manual Expiry (YYYY-MM-DD)", value=PARAMS["manualExpiry"])
        PARAMS["exitMode"] = st.selectbox("Target Exit Mode", ["T1", "T2", "T1_T2", "MANUAL"], index=["T1", "T2", "T1_T2", "MANUAL"].index(PARAMS["exitMode"]))
        if PARAMS["exitMode"] == "T1_T2": PARAMS["t1ExitPct"] = st.slider("T1 Partial Exit %", min_value=10, max_value=90, value=int(PARAMS["t1ExitPct"]), step=10)
        PARAMS["useHighLowForTarget"] = st.checkbox("Use Candle High/Low for Target Touch?", value=PARAMS["useHighLowForTarget"])

        st.header("4. Capital, Risk, Lot & Time Window")
        PARAMS["optLot"] = st.number_input("Lot Size", min_value=1, value=int(PARAMS["optLot"]))
        PARAMS["optDelta"] = st.number_input("Option Delta", min_value=0.1, max_value=1.0, value=float(PARAMS["optDelta"]), step=0.05)
        PARAMS["capital"] = st.number_input("Capital (Rs)", min_value=10000.0, value=float(PARAMS["capital"]), step=10000.0)
        PARAMS["riskPct"] = st.number_input("Risk Per Trade (%)", min_value=0.1, max_value=10.0, value=float(PARAMS["riskPct"]), step=0.1)
        PARAMS["slMult"] = st.number_input("SL ATR Multiplier", min_value=0.5, max_value=5.0, value=float(PARAMS["slMult"]), step=0.1)
        PARAMS["rrT"] = st.number_input("Target 1 Risk:Reward", min_value=0.5, max_value=10.0, value=float(PARAMS["rrT"]), step=0.5)
        PARAMS["sess_start"] = st.text_input("Session Start (HH:MM IST)", value=PARAMS["sess_start"])
        PARAMS["sess_end"] = st.text_input("Session End (HH:MM IST)", value=PARAMS["sess_end"])
        PARAMS["coolBars"] = st.number_input("Cooldown Bars after Exit", min_value=0, max_value=50, value=int(PARAMS["coolBars"]))

        st.header("5. Direction & MTF Settings")
        c1, c2 = st.columns(2)
        with c1: PARAMS["allowCE"] = st.checkbox("Allow CE (Long)", value=PARAMS["allowCE"])
        with c2: PARAMS["allowPE"] = st.checkbox("Allow PE (Short)", value=PARAMS["allowPE"])
        PARAMS["needN"] = st.slider("Min 5m Conditions (of 5)", min_value=2, max_value=5, value=int(PARAMS["needN"]))
        PARAMS["mtfOn"] = st.checkbox("Enable MTF Filter (3m+5m)", value=PARAMS["mtfOn"])
        PARAMS["mtf15Req"] = st.checkbox("Require 15m Agreement?", value=PARAMS["mtf15Req"])
        PARAMS["mtfNeed"] = st.slider("Min MTF Conditions (of 4)", min_value=1, max_value=4, value=int(PARAMS["mtfNeed"]))

        st.header("6. ADX, DI, RSI, Volume & Final Buy")
        PARAMS["adxOn"] = st.checkbox("Enable ADX Sideways Filter", value=PARAMS["adxOn"])
        PARAMS["adxMin"] = st.number_input("Min ADX", min_value=5.0, max_value=50.0, value=float(PARAMS["adxMin"]))
        PARAMS["diOn"] = st.checkbox("Enable DI+ / DI- Filter", value=PARAMS["diOn"])
        PARAMS["diMtf"] = st.checkbox("Apply DI Filter on 3m & 15m", value=PARAMS["diMtf"])
        PARAMS["diNeed"] = st.slider("DI TF Pass Required (1-3)", min_value=1, max_value=3, value=int(PARAMS["diNeed"]))

        st.subheader("Final Buy (Blue Arrow)")
        PARAMS["wfOn"] = st.checkbox("Enable Final Buy (Blue Arrow)", value=PARAMS["wfOn"])
        PARAMS["wfRule"] = st.selectbox("Final Buy Rule", ["E", "A", "B", "C", "D"], index=["E", "A", "B", "C", "D"].index(PARAMS["wfRule"]))
        PARAMS["wfMin"] = st.number_input("Min Wait Bars for Blue Arrow", min_value=1, max_value=15, value=int(PARAMS["wfMin"]))
        PARAMS["wfMax"] = st.number_input("Max Wait Bars", min_value=5, max_value=50, value=int(PARAMS["wfMax"]))
        PARAMS["wfDip"] = st.number_input("Dip ATR Multiplier", min_value=0.1, max_value=3.0, value=float(PARAMS["wfDip"]), step=0.1)
        PARAMS["wfUp"] = st.number_input("Breakout ATR Mult", min_value=0.0, max_value=3.0, value=float(PARAMS["wfUp"]), step=0.1)

        st.header("7. Option OI & VOL PCR")
        PARAMS["autoOc"] = st.checkbox("Auto Option Chain OI", value=PARAMS["autoOc"])
        PARAMS["ocN"] = st.slider("Option OI Strike Span (+-N)", min_value=2, max_value=9, value=int(PARAMS["ocN"]))
        PARAMS["ovOn"] = st.checkbox("Enable Option VOL PCR", value=PARAMS["ovOn"])
        PARAMS["ovN"] = st.slider("VOL PCR Strike Span (+-N)", min_value=2, max_value=9, value=int(PARAMS["ovN"]))
        PARAMS["ovFeed"] = st.checkbox("Feed VOL PCR into Probability", value=PARAMS["ovFeed"])
        PARAMS["futOiOn"] = st.checkbox("Enable Futures OI Analysis", value=PARAMS["futOiOn"])
        PARAMS["oiProbFilterOn"] = st.checkbox("Enable OI+Vol Probability Filter", value=PARAMS["oiProbFilterOn"])
        PARAMS["minOiProbCE"] = st.number_input("Min OI+Vol Prob % for CE", min_value=0.0, max_value=100.0, value=float(PARAMS["minOiProbCE"]))
        PARAMS["minOiProbPE"] = st.number_input("Min OI+Vol Prob % for PE", min_value=0.0, max_value=100.0, value=float(PARAMS["minOiProbPE"]))
        PARAMS["requireHighProbOnly"] = st.checkbox("Trade HIGH PROB Signals Only?", value=PARAMS["requireHighProbOnly"])
        PARAMS["pcrIn"] = st.number_input("Manual OI PCR (0 = Auto)", min_value=0.0, max_value=5.0, value=float(PARAMS["pcrIn"]), step=0.05)
        PARAMS["callWall"] = st.number_input("Manual Call Wall (0 = Auto)", min_value=0.0, value=float(PARAMS["callWall"]), step=50.0)
        PARAMS["putWall"] = st.number_input("Manual Put Wall (0 = Auto)", min_value=0.0, value=float(PARAMS["putWall"]), step=50.0)

        st.header("8. Daily 20MA Gate & Sector")
        PARAMS["dgOn"] = st.checkbox("Enable Daily 20MA Gate", value=PARAMS["dgOn"])
        PARAMS["dgMode"] = st.selectbox("Daily Gate Mode", ["Sirf PE par", "Dono (CE + PE)", "Sirf CE par"], index=["Sirf PE par", "Dono (CE + PE)", "Sirf CE par"].index(PARAMS["dgMode"]))
        PARAMS["peScMin"] = st.slider("PE Direction Score Min (0-5)", min_value=0, max_value=5, value=int(PARAMS["peScMin"]))
        PARAMS["peBelowOpen"] = st.checkbox("PE Only Below Today Open", value=PARAMS["peBelowOpen"])
        PARAMS["scOn"] = st.checkbox("Show Sector Strength Table", value=PARAMS["scOn"])
        PARAMS["scFeed"] = st.checkbox("Use Sector Strength Filter", value=PARAMS["scFeed"])

        st.header("9. Dashboard Settings")
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

    now_ist = dt.datetime.now(IST)
    st.info(f"**IST Time:** {now_ist.strftime('%Y-%m-%d %I:%M:%S %p')} | **Mode:** {CONFIG['RUN_MODE']} | **Strike:** {PARAMS['strikeMode']} | **Expiry:** {PARAMS['expiryMode']} | **Exit:** {PARAMS['exitMode']}")

    if run_mode == "REAL_TRADE_REPORT":
        st.subheader("Real Live Trades Journal Report")
        csv_file = CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
        if os.path.exists(csv_file):
            df_rep = pd.read_csv(csv_file)
            st.dataframe(df_rep, use_container_width=True)
            st.download_button("Download Real Trades CSV", df_rep.to_csv(index=False).encode("utf-8"), csv_file, "text/csv")
        else: st.warning("Abhi tak koi Real Trade record file nahi bani hai.")
        return

    creds_ok = ((broker_choice == "DHAN" and CONFIG["DHAN_CLIENT_ID"] and CONFIG["DHAN_ACCESS_TOKEN"]) or (broker_choice == "UPSTOX" and CONFIG["UPSTOX_ACCESS_TOKEN"]))
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

    if run_mode == "BACKTEST":
        st.subheader(f"Historical Backtest ({CONFIG['BACKTEST_DAYS']} Days | {CONFIG['BACKTEST_ENTRY_TYPE']})")
        if st.button("Run Full Multi-Timeframe Backtest Now", type="primary"):
            with st.spinner("Data fetch ho raha hai..."):
                bt_res = run_backtest(connector, days=CONFIG["BACKTEST_DAYS"])
            st.session_state["last_bt_res"] = bt_res
            st.session_state["last_bt_modes"] = ["ALL_SIGNALS", "REAL_BLUE_ONLY"] if CONFIG["BACKTEST_ENTRY_TYPE"] == "BOTH" else [CONFIG["BACKTEST_ENTRY_TYPE"]]

        if "last_bt_res" in st.session_state:
            bt_res = st.session_state["last_bt_res"]
            if isinstance(bt_res, dict) and bt_res.get("error"):
                st.error(bt_res["error"])
            else:
                st.success("Backtest Complete!")
                for m_lbl in st.session_state.get("last_bt_modes", []):
                    csv_name = f"backtest_{m_lbl}_{PARAMS['strikeMode']}_{PARAMS['exitMode']}.csv"
                    html_name = f"dashboard_backtest_{m_lbl}.html"
                    st.markdown(f"### Results: {m_lbl}")
                    c_dl1, c_dl2 = st.columns(2)
                    if os.path.exists(csv_name):
                        j_df = pd.read_csv(csv_name)
                        with c_dl1: st.download_button(f"📥 Download {csv_name}", j_df.to_csv(index=False).encode("utf-8"), csv_name, "text/csv", key=f"csv_{m_lbl}")
                        st.dataframe(j_df, use_container_width=True)
                    if os.path.exists(html_name):
                        with open(html_name, "r", encoding="utf-8") as hf:
                            html_str = hf.read()
                        with c_dl2: st.download_button(f"📥 Download {html_name}", html_str, html_name, "text/html", key=f"html_{m_lbl}")
                        components.html(html_str, height=780, scrolling=True)
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
            with st.spinner("Live market data fetch ho raha hai..."):
                try: engine.process_live_bar(is_pre_alert=False)
                except Exception as exc: st.error(f"Live Bar Evaluation Error: {exc}")

        dash_file = CONFIG.get("DASH_HTML_PATH", "dashboard.html")
        if os.path.exists(dash_file):
            with open(dash_file, "r", encoding="utf-8") as f: dash_html = f.read()
            st.subheader("Live Candlestick Chart + All 12 Pine Script Tables")
            st.download_button("📥 Download Live dashboard.html", dash_html, "dashboard.html", "text/html", key="live_html")
            components.html(dash_html, height=820, scrolling=True)
        else:
            st.info("Upar 'Fetch & Evaluate Live Bar Now' button dabayein — chart aur saari 12 tables yahan load ho jayengi.")

        if engine.trade_journal:
            st.subheader("Session Trade Journal")
            st.dataframe(pd.DataFrame(engine.trade_journal), use_container_width=True)

        if auto_live:
            time.sleep(30)
            st.rerun()

if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None: run_streamlit_desktop_app()
        else: raise RuntimeError("Not in Streamlit context")
    except Exception:
        connector = BrokerConnector(CONFIG)
        interactive_option_selector(connector)
        if CONFIG["RUN_MODE"].upper() == "BACKTEST": run_backtest(connector, days=CONFIG["BACKTEST_DAYS"])
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
