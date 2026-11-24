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

Dashboard bot se khud jud gaya hai: har closed 5m bar ke baad dashboard.html update hota hai.
Backtest ke end me dashboard_backtest_<MODE>.html banta hai.
Settings:  CONFIG["DASH_ON"], CONFIG["DASH_HTML_PATH"], CONFIG["DASH_CONSOLE_TABLES"]  aur  DASH{} (table positions / show-hide).
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
import streamlit as st
import streamlit.components.v1 as components

# ==============================================================================
# 0. STREAMLIT UI & DIRECT CREDENTIAL INPUTS (Sidebar)
# ==============================================================================
st.set_page_config(page_title="Nifty Option Signal PRO v28", layout="wide")

st.sidebar.title("🔐 Broker & API Settings")
ui_broker = st.sidebar.selectbox("Select Broker", ["DHAN", "UPSTOX"], index=0)
ui_chart_sym = st.sidebar.selectbox("Chart Symbol", ["NIFTY_SPOT", "NIFTY_FUT"], index=0)
ui_client_id = st.sidebar.text_input("Dhan Client ID", value=os.environ.get("DHAN_CLIENT_ID", ""))
ui_access_token = st.sidebar.text_input("Broker Access Token", type="password", value=os.environ.get("DHAN_ACCESS_TOKEN", ""))

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Strategy & Execution Controls")
ui_run_mode = st.sidebar.selectbox("Run Mode", ["LIVE", "BACKTEST"], index=0)
ui_bt_days = st.sidebar.number_input("Backtest Days", min_value=1, max_value=180, value=30)
ui_bt_type = st.sidebar.selectbox("Backtest Entry Type", ["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"], index=0)
ui_strike_mode = st.sidebar.selectbox("Strike Mode", ["ATM", "ITM_1", "ITM_2", "OTM_1"], index=0)
ui_expiry_mode = st.sidebar.selectbox("Expiry Mode", ["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"], index=0)
ui_manual_expiry = st.sidebar.text_input("Manual Expiry (YYYY-MM-DD)", value="")
ui_exit_mode = st.sidebar.selectbox("Exit Mode", ["T1", "T2", "T1_T2", "MANUAL"], index=0)
ui_oc_n = st.sidebar.slider("Option OI Strike Span (+- N)", min_value=2, max_value=9, value=4)
ui_ov_n = st.sidebar.slider("VOL PCR Strike Span (+- N)", min_value=2, max_value=9, value=5)
ui_auto_order = st.sidebar.checkbox("Auto Place Live Order (Real Trades)", value=False)

# ==============================================================================
# 1. BROKER, CHART, EXECUTION & TELEGRAM CONFIG (GitHub Secrets + Direct Support)
# ==============================================================================
CONFIG = {
    "BROKER": ui_broker,              # "DHAN" ya "UPSTOX"
    "CHART_SYMBOL": ui_chart_sym,  # "NIFTY_SPOT" ya "NIFTY_FUT"

    # Dhan API Credentials (Direct paste karein ya GitHub Secrets se auto-load hoga)
    "DHAN_CLIENT_ID": ui_client_id,
    "DHAN_ACCESS_TOKEN": ui_access_token,

    # Upstox API Credentials
    "UPSTOX_ACCESS_TOKEN": ui_access_token if ui_broker == "UPSTOX" else os.environ.get("UPSTOX_ACCESS_TOKEN", ""),

    # Telegram Alerts (Optional)
    "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),

    # Run Mode & Order Execution
    "RUN_MODE": ui_run_mode,            # "LIVE" = Real-time Market Algo | "BACKTEST" = Historical Backtest
    "BACKTEST_DAYS": int(ui_bt_days),           # Backtest kitne din ke historical data par chalana hai
    "BACKTEST_ENTRY_TYPE": ui_bt_type, # "ALL_SIGNALS" | "REAL_BLUE_ONLY" | "BOTH"
    "AUTO_PLACE_ORDER": ui_auto_order,     # True = Blue Arrow par Live Order jayega | False = Sirf Alert/Log
    "PRODUCT_TYPE": "INTRADAY",
    "INTERACTIVE_MENU": False,      # True = Run karte hi screen par Option Selection Menu aayega
    "REAL_TRADES_CSV": "live_real_trades_journal.csv",  # Real Live Trades ka permanent record file

    # Dashboard (nifty_dash)
    "DASH_ON": True,                       # True = chart + tables dashboard.html banao
    "DASH_HTML_PATH": "dashboard.html",    # Live dashboard file ka naam
    "DASH_CONSOLE_TABLES": False,          # True = har bar par saari tables console me bhi print hongi
}

# ==============================================================================
# 2. COMPLETE INDICATOR SETTINGS (100% EXACT PINE SCRIPT v28 + VOL PCR)
# ==============================================================================
PARAMS = {
    # --- STRIKE & EXPIRY SELECTION OPTIONS ---
    "strikeMode": ui_strike_mode,           # Options: "ATM", "ITM_1", "ITM_2", "OTM_1"
    "expiryMode": ui_expiry_mode,  # Options: "CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"
    "manualExpiry": ui_manual_expiry,            # Sirf expiryMode="MANUAL" ke liye (e.g., "2026-11-24")

    # --- TARGET EXIT OPTIONS (Live Algo + Backtest Dono Ke Liye) ---
    "exitMode": ui_exit_mode,              # Options: "T1", "T2", "T1_T2", "MANUAL"
    "t1ExitPct": 50,               # "T1_T2" mode me T1 par kitne % lots book karne hain
    "useHighLowForTarget": True,   # True = Candle High/Low touch par T1/T2 exit | False = Sirf Candle Close par

    # --- G0: Chart, Market Window & Trade Settings ---
    "chartType": "Index/Fut",      # "Index/Fut", "CE prem", "PE prem"
    "optStep": 50.0,               # Strike Step (Nifty 50 = 50, BankNifty = 100)
    "optLot": 65,                  # Lot Size (NSE/broker se verify karein)
    "optDelta": 0.5,               # Approx Option Delta (0.1 to 1.0)
    "slMult": 1.5,                 # SL = ATR(10) x
    "rrT": 2.0,                    # Target 1 Risk:Reward
    "capital": 100000.0,           # Capital (Rs)
    "riskPct": 1.0,                # Risk per trade % of capital
    "needN": 4,                    # Signal ke liye min conditions (of 5)
    "orBars": 3,                   # Opening Range bars (3 x 5m = 15 min)
    "sess_start": "09:20",         # Market Trade Window Start (IST)
    "sess_end": "15:00",           # Market Trade Window End (IST)
    "extMult": 3.0,                # Peak chase band: price EMA21 se itne ATR se door ho to skip
    "coolBars": 6,                 # Exit ke baad itne bar nayi entry nahi (6 x 5m = 30 min)

    # MTF Toggles (3m, 5m, 15m, 1h, 4h)
    "mtfOn": True,                 # 3m + 5m (+ 15m) agree toggle
    "mtf15Req": False,             # True = 15m zaroori | False = buy 3m+5m se, 15m bullish/bearish ho to '+'
    "mtfNeed": 3,                  # Har extra timeframe par min conditions (of 4)

    # Sideways & DI Filter Toggles
    "adxOn": True,                 # Sideways filter: ADX kam ho to signal band
    "adxLen": 14,                  # ADX length
    "adxMin": 20.0,                # ADX itne se kam = sideways (signal band)
    "diOn": True,                  # DI filter ON: CE me D+ upar aur D- neeche, PE me ulta
    "diMtf": True,                 # DI filter 3m aur 15m par bhi ON/OFF (False = sirf 5m)
    "diNeed": 2,                   # 5m / 3m / 15m me se kitne TF pass hone chahiye (1 se 3)
    "adxTrd": 20.0,                # DI filter: ADX itne se UPAR ho
    "diStrong": 20.0,              # Signal side DI itne se UPAR ho
    "diWeak": 20.0,                # Ulta side DI itne se NEECHE ho

    # Direction & PE Specific Filters
    "allowCE": True,               # CE signal ON/OFF (Long)
    "allowPE": True,               # PE signal ON/OFF (Short)
    "peBrMax": 100.0,              # PE sirf tab jab Breadth Score <= itna (100 = OFF)
    "peAdxMin": 0.0,               # PE ke liye alag min ADX (0 = OFF)
    "peHtf": "1h PE",              # "OFF", "1h PE", "1h + 4h PE"
    "peBelowOpen": True,           # PE sirf tab jab price aaj ke open ke neeche ho
    "optSym": "",                  # Specific Option Symbol - khali = Auto Strike/Expiry
    "optEntry": 0.0,               # Option manual entry premium (0 = auto)

    # --- G5: Final Buy (Green/Red Arrow -> Calculation -> Blue Arrow) ---
    "wfOn": True,                  # Final Buy arrow & 2-step confirmation ON/OFF
    "wfMin": 1,                    # Final Buy signal candle ke kam se kam itne candle baad hi
    "wfRule": "E",                 # "A" (Dip+ATR), "B" (Sig Close), "C" (Dip+Wick), "D" (MA Cross), "E" (Simple Dip+Rev)
    "wfA": 0.5,                    # A rule: dip low se itne ATR(10) upar close ho
    "wfDip": 0.5,                  # C rule: signal close se min dip (ATR x)
    "wfWk": 40,                    # C rule: reversal candle wick %
    "wfF": 3,                      # D rule: Fast MA length
    "wfS": 5,                      # D rule: Slow MA length
    "wfMax": 20,                   # Max candles wait for Final Buy (uske baad cancel)
    "wfUp": 0.5,                   # Dip nahi aaya to signal close se ATR x upar/neeche breakout (0 = OFF)
    "wfUpPts": 0.0,                # Fixed points breakout (0 = ATR setting use hogi)
    "wfWick": True,                # True = Dip original SL ki wick touch kare to bhi cancel | False = sirf close

    # --- G7: Daily 20MA Direction Gate (7 din / 5 din) ---
    "dgOn": True,                  # Daily 20MA gate ON/OFF
    "dgMode": "Sirf PE par",       # "Dono (CE + PE)", "Sirf PE par", "Sirf CE par"
    "peScMin": 3,                  # PE direction score: 5 shart me se min kitni pass hon (0 = OFF, 0 to 5)
    "dgLen": 20,                   # Daily Moving Average length
    "dgD1": 7,                     # Pehla check: kitne daily candle pehle
    "dgD2": 5,                     # Doosra check: kitne daily candle pehle
    "dgFlat": 0.05,                # MA ek din me itne % se kam hile = flat

    # --- G8: v22 Upgrades (Sab default False = exact v28 default; True karke ON karein) ---
    "lateOn": False,               # Late-entry guard: ADX aur Breadth dono bahut high ho to skip
    "lateAdx": 40.0,
    "lateBr": 90.0,
    "arOn": False,                 # ADX rising: ADX pichhle arN bar se badh raha ho
    "arN": 3,
    "rsiOn": False,                # RSI cap: CE me RSI > rsiHi / PE me < rsiLo ho to skip
    "rsiHi": 76.0,
    "rsiLo": 24.0,
    "cdOn": False,                 # Candle strength: CE me close high ke paas, PE me low ke paas
    "cdPos": 0.6,
    "vfOn": False,                 # Volume confirm: volume 20 bar average se kam na ho
    "vfMult": 1.0,
    "lvlOn": False,                # Level guard: CE PDH ke paas / PE PDL ke paas to skip
    "lvlBuf": 0.15,
    "rdOn": False,                 # Round level guard: 100-pt round level ke paas skip
    "rdStep": 100.0,
    "rdPts": 15.0,
    "opOn": False,                 # CE sirf tab jab price aaj ke open ke upar ho
    "vxOn": False,                 # India VIX: CE me VIX badh na raha ho, PE me gir na raha ho
    "vxLook": 12,
    "tmOn": False,                 # Time filter: neeche ke 3 band windows me nayi entry nahi
    "tmS1": ("09:20", "09:35"),
    "tmS2": ("12:00", "13:30"),
    "tmS3": ("14:45", "15:00"),
    "exOn": False,                 # Expiry day par nayi entry nahi
    "exDay": "Tuesday",            # "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
    "beOn": False,                 # Breakeven: price +beR risk chala jaye to SL entry par
    "beR": 1.0,
    "beLock": 0.1,
    "trOn": False,                 # Trail: T1 par exit nahi, SL +1R par lock, exit T2 par
    "gdA": 8,                      # Grade A: 9 me se min pass
    "gdB": 6,                      # Grade B: 9 me se min pass

    # --- G3, G4, G9: OPTION OI + OPTION VOLUME PCR + FUTURES OI (STRIKE RANGE 2..9) ---
    "autoOc": True,                # Option Chain OI Auto ON/OFF (Dhan/Upstox API se asli OI)
    "ocN": int(ui_oc_n),                      # Option OI ke liye ATM +- N strikes (Options: 2,3,4,5,6,7,8,9)
    "pcrIn": 0.0,                  # Manual OI PCR (0 = OFF)
    "callWall": 0.0,               # Manual Call Wall (0 = OFF)
    "putWall": 0.0,                # Manual Put Wall (0 = OFF)
    "wallBuf": 0.3,                # Wall ke itne % paas aane par us side ka trade skip
    "pcrBull": 1.1,
    "pcrBear": 0.9,

    "ovOn": True,                  # VOL PCR indicator ON/OFF
    "ovN": int(ui_ov_n),                      # Option Volume ke liye ATM +- N strikes (Options: 2,3,4,5,6,7,8,9)
    "ovBull": 1.2,
    "ovBear": 0.8,
    "ovFeed": True,                # True = VOL PCR aur Volume Wall ko trade probability & filter me lagao

    "futOiOn": True,               # Futures OI analysis ON/OFF
    "oiLook": 12,                  # Futures OI / price change kitne bar peeche se

    "oiProbFilterOn": True,        # True = Min Combined OI+Volume Probability % pass hone par hi entry
    "minOiProbCE": 55.0,           # CE Buy ke liye minimum OI+Vol Bullish Probability %
    "minOiProbPE": 55.0,           # PE Buy ke liye minimum OI+Vol Bearish Probability %
    "requireHighProbOnly": False,  # True = Sirf 'HIGH PROB' signals pe trade | False = HIGH PROB + medium

    # --- G1: Pre-Alert & Display ---
    "preSec": 15,                  # Pre-alert: candle close se itne second pehle warning alert (0 = band)

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
# 2B. DASHBOARD DISPLAY SETTINGS (nifty_dash tables / chart ki position aur show-hide)
# ==============================================================================
_dd = dt.date.today()
DASH = {
    "textSz": "tiny",              # "tiny", "small", "normal" (table font)
    "showDetail": True,            # True = SIGNAL table ki saari detail rows (Bull/Bear, EMA, VWAP, RSI, ADX ...)
    "showMk": True,                # Chart par BUY/EXIT markers
    "lblMode": "ON",               # "ON" = marker par poora text | "OFF" = sirf BUY CE / BUY PE / EXIT
    "lblBars": 0,
    "wfArrow": True,               # Chart par FINAL BUY (blue) arrow
    "wfMaShow": False,             # Final Buy rule D ki fast/slow MA line chart par
    # Table positions: Top Left/Center/Right, Middle Left/Right, Bottom Left/Center/Right
    "posSig": "Top Right", "posLg": "Bottom Right", "posBr": "Top Left", "posOi": "Middle Left",
    "posLs": "Bottom Left", "scPos": "Top Center", "scPosA": "Middle Right", "posJ": "Bottom Center",
    "posPh": "Bottom Center", "posXs": "Middle Right", "gdPos": "Top Center", "vp_pos": "Middle Left",
    # Table show/hide
    "showLog": True, "showList": True, "scAll": True, "jShow": True, "phShow": True,
    "xsShow": True, "gdShow": True, "vp_showTbl": True,
    "jPg": 1,                      # Journal page number
    "vp_useSpot": True,            # VOL PCR table me spot/chart source dikhane ke liye
    # Phase-wise stats ke dates (entry date se): P1 = ph1S..ph2S, P2 = ph2S..phE
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
    """
    Algo ne ab tak kitne REAL LIVE TRADES liye hain (Local CSV + Broker Order/Trade Book),
    un sabhi ka poora hisab aur P&L report dikhata hai.
    """
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

    # 1. Mode Selection (LIVE vs BACKTEST vs REAL TRADE REPORT)
    print("\n[1] Mode Chunein:")
    print("    1 = LIVE Trading / Alerts (Default)")
    print("    2 = BACKTEST (Historical Check - Bina Live Trade Liye Bhi Chalega)")
    print("    3 = REAL TRADE REPORT (Algo Ne Ab Tak Kitne Real Trade Liye Uska Hisab Dekhein)")
    m_in = input("    Option number dalein (Enter = 1): ").strip()

    if m_in == "3":
        show_real_trade_report(connector)
        cont = input("Kya ab LIVE ya BACKTEST chalana hai? (1 = LIVE, 2 = BACKTEST, Enter = Exit): ").strip()
        if cont not in ("1", "2"):
            raise SystemExit(0)
        m_in = cont

    if m_in == "2":
        CONFIG["RUN_MODE"] = "BACKTEST"
        d_in = input(f"    Kitne din ka Backtest chahiye? (Enter = {CONFIG['BACKTEST_DAYS']}): ").strip()
        if d_in.isdigit() and int(d_in) > 0:
            CONFIG["BACKTEST_DAYS"] = int(d_in)

        print("\n[1B] Backtest Type Chunein (Same Data Par):")
        print("    1 = BOTH (Initial Signals + Real Blue Arrow Final Buy Dono Ka Comparison)")
        print("    2 = REAL_BLUE_ONLY (Sirf Real Trade - Blue Arrow Final Buy Confirm Hone Par Entry)")
        print("    3 = ALL_SIGNALS (Har Initial Green/Red Arrow Signal Par Entry)")
        bt_in = input("    Option number dalein (Enter = 1 BOTH): ").strip()
        bt_map = {"1": "BOTH", "2": "REAL_BLUE_ONLY", "3": "ALL_SIGNALS"}
        if bt_in in bt_map:
            CONFIG["BACKTEST_ENTRY_TYPE"] = bt_map[bt_in]
    else:
        CONFIG["RUN_MODE"] = "LIVE"

    # 2. Strike Selection (ATM vs ITM_1 vs ITM_2 vs OTM_1)
    print("\n[2] Strike Selection (Kaun sa Option Buy Karna Hai):")
    print("    1 = ATM (Round Figure ATM - e.g. 25500 CE/PE)")
    print("    2 = ITM 1 (In-The-Money 1 Step - e.g. CE: 25450 / PE: 25550)")
    print("    3 = ITM 2 (In-The-Money 2 Step - e.g. CE: 25400 / PE: 25600)")
    print("    4 = OTM 1 (Out-Of-The-Money 1 Step - e.g. CE: 25550 / PE: 25450)")
    s_in = input("    Option number dalein (Enter = 1 ATM): ").strip()
    strike_map = {"1": "ATM", "2": "ITM_1", "3": "ITM_2", "4": "OTM_1"}
    if s_in in strike_map:
        PARAMS["strikeMode"] = strike_map[s_in]

    # 3. Expiry Selection
    print("\n[3] Expiry Selection:")
    avail_exps = []
    if connector is not None:
        try:
            avail_exps = connector.get_all_upcoming_expiries()
        except Exception:
            avail_exps = []

    if avail_exps:
        print(f"    Broker Upcoming Expiries: {', '.join(avail_exps[:5])}")
    print("    1 = CURRENT_WEEK (Is Hafte Ki Nearest Expiry)")
    print("    2 = NEXT_WEEK    (Agle Hafte Ki Weekly Expiry)")
    print("    3 = MONTHLY      (Is Mahine Ki Monthly Expiry)")
    print("    4 = MANUAL       (Khud Date Dalein YYYY-MM-DD)")
    e_in = input("    Option number dalein (Enter = 1 CURRENT_WEEK): ").strip()
    exp_map = {"1": "CURRENT_WEEK", "2": "NEXT_WEEK", "3": "MONTHLY", "4": "MANUAL"}
    if e_in in exp_map:
        PARAMS["expiryMode"] = exp_map[e_in]
        if PARAMS["expiryMode"] == "MANUAL":
            dt_in = input("    Expiry Date likhein (e.g. 2026-11-24): ").strip()
            if dt_in:
                PARAMS["manualExpiry"] = dt_in

    # 4. Target Exit Selection (T1, T2, T1_T2, MANUAL)
    print("\n[4] Target Exit Option Chunein:")
    print("    1 = T1     (Target 1 hit hote hi 100% exit)")
    print("    2 = T2     (T1 par SL +1R trail, Target 2 par 100% exit)")
    print("    3 = T1_T2  (50% T1 par book + SL Entry par, baaki 50% T2 par exit)")
    print("    4 = MANUAL (Auto Target exit OFF - jab chahein tab exit karein)")
    x_in = input("    Option number dalein (Enter = 1 T1): ").strip()
    exit_map = {"1": "T1", "2": "T2", "3": "T1_T2", "4": "MANUAL"}
    if x_in in exit_map:
        PARAMS["exitMode"] = exit_map[x_in]

    # 5. Option OI & Volume Strike Span (2 to 9)
    print("\n[5] Option OI & Volume Strike Range (ATM se Upar aur Neeche kitne strike: 2 se 9):")
    oi_in = input(f"    Option OI Strike Span dalein [2-9] (Enter = {PARAMS['ocN']}): ").strip()
    if oi_in.isdigit() and 2 <= int(oi_in) <= 9:
        PARAMS["ocN"] = int(oi_in)
    vol_in = input(f"    Option Volume PCR Strike Span dalein [2-9] (Enter = {PARAMS['ovN']}): ").strip()
    if vol_in.isdigit() and 2 <= int(vol_in) <= 9:
        PARAMS["ovN"] = int(vol_in)

    # 6. Auto Order Confirmation (Only for LIVE mode)
    if CONFIG["RUN_MODE"] == "LIVE":
        print("\n[6] Order Execution Mode:")
        print("    1 = SIRF ALERTS (Safe Mode - Blue Arrow par alert aayega, order nahi lagega)")
        print("    2 = AUTO LIVE ORDER (Blue Arrow par Broker me real order lag jayega)")
        o_in = input("    Option number dalein (Enter = 1 Safe Alert Mode): ").strip()
        CONFIG["AUTO_PLACE_ORDER"] = (o_in == "2")

    # 7. Dashboard (chart + tables)
    print("\n[7] Dashboard (candle chart + 12 tables -> dashboard.html):")
    print("    1 = ON (Default)   2 = OFF   3 = ON + tables console me bhi")
    d_in2 = input("    Option number dalein (Enter = 1 ON): ").strip()
    CONFIG["DASH_ON"] = (d_in2 != "2")
    CONFIG["DASH_CONSOLE_TABLES"] = (d_in2 == "3")

    print("\n" + "-" * 68)
    print(f"SELECTED -> Mode: {CONFIG['RUN_MODE']} ({CONFIG['BACKTEST_ENTRY_TYPE']}) | Strike: {PARAMS['strikeMode']} | Expiry: {PARAMS['expiryMode']} | Exit: {PARAMS['exitMode']} | OI: +-{PARAMS['ocN']} | Vol: +-{PARAMS['ovN']}")
    print("-" * 68 + "\n")


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
            from dhanhq import dhanhq
            self.dhan = dhanhq(cfg["DHAN_CLIENT_ID"], cfg["DHAN_ACCESS_TOKEN"])
        elif self.broker == "UPSTOX":
            self.headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {cfg['UPSTOX_ACCESS_TOKEN']}"
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
            if not fut.empty:
                m["NIFTY_FUT"] = fut.iloc[0]["instrument_key"]
            eq = df[df["segment"] == "NSE_EQ"]
            for sym, _ in BREADTH_STOCKS:
                row = eq[eq["trading_symbol"] == sym]
                if not row.empty:
                    m[sym] = row.iloc[0]["instrument_key"]
            m["_DF"] = df
        return m

    def get_broker_live_trade_summary(self) -> str:
        """Broker API se aaj ke actual executed orders aur positions ka count aur detail nikalta hai."""
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

    def get_candles(self, key: str, interval: str = "5", days: int = 10) -> pd.DataFrame:
        to_dt = dt.datetime.now(IST)
        from_dt = to_dt - dt.timedelta(days=days)

        if self.broker == "DHAN":
            sec_id = self.inst.get(key)
            if not sec_id:
                return pd.DataFrame()
            seg = "IDX_I" if key in ("NIFTY_SPOT", "INDIAVIX") else ("NSE_FNO" if key == "NIFTY_FUT" else "NSE_EQ")
            itype = "INDEX" if seg == "IDX_I" else ("FUTIDX" if seg == "NSE_FNO" else "EQUITY")

            if interval == "D":
                res = self.dhan.historical_daily_data(
                    security_id=sec_id, exchange_segment=seg, instrument_type=itype,
                    from_date=from_dt.strftime("%Y-%m-%d"), to_date=to_dt.strftime("%Y-%m-%d")
                )
            else:
                req_int = "1" if interval == "3" else ("60" if interval == "240" else interval)
                res = self.dhan.intraday_minute_data(
                    security_id=sec_id, exchange_segment=seg, instrument_type=itype,
                    from_date=from_dt.strftime("%Y-%m-%d 09:15:00"), to_date=to_dt.strftime("%Y-%m-%d 15:30:00"),
                    interval=int(req_int)
                )
            d = res.get("data", {})
            if not d or "timestamp" not in d or len(d["timestamp"]) == 0:
                return pd.DataFrame()
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert(IST),
                "open": d["open"], "high": d["high"], "low": d["low"],
                "close": d["close"],
                "volume": d.get("volume", [0] * len(d["close"])),
                "oi": d.get("open_interest", [0] * len(d["close"]))
            }).set_index("timestamp").sort_index()

        elif self.broker == "UPSTOX":
            ikey = self.inst.get(key)
            if not ikey:
                return pd.DataFrame()
            umap = {"1": ("minutes", "1"), "3": ("minutes", "1"), "5": ("minutes", "5"),
                    "15": ("minutes", "15"), "60": ("hours", "1"), "240": ("hours", "1"), "D": ("days", "1")}
            utype, uval = umap[interval]
            r1 = requests.get(
                f"https://api.upstox.com/v3/historical-candle/{ikey}/{utype}/{uval}/{to_dt.strftime('%Y-%m-%d')}/{from_dt.strftime('%Y-%m-%d')}",
                headers=self.headers, timeout=10
            ).json()
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
                    self.dhan.place_order(
                        security_id=sec_id,
                        exchange_segment=self.dhan.NSE_FNO,
                        transaction_type=txn,
                        quantity=qty,
                        order_type=self.dhan.MARKET,
                        product_type=self.dhan.INTRA,
                        price=0
                    )
                    return True
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
                    requests.post("https://api.upstox.com/v2/order/place", json=payload, headers=self.headers, timeout=10)
                    return True
        except Exception as e:
            print(f"[Order Placement Error] {e}")
        return False


# ==============================================================================
# 4B. DASHBOARD (nifty_dash.py): TABLES + CONSOLE + HTML CHART
# ==============================================================================
NAN = float("nan")
SECTOR_NAMES = list(SECTOR_MAP.keys())   # 15 sector (breadth/sector table ke liye)


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


# ------------------------------------------------------------------------------
def build_tables(eng, o, D, vp, C):
    tabs = []
    unit = "%" if o.isPrem else "p"
    fl = C.flatPct

    # ---------------------------------------------------------------- SIGNAL TABLE (st)
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
    # option rows (OPTION SYMBOL box)
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

    # ---------------------------------------------------------------- SIGNAL LOG (lgt)
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

    # ---------------------------------------------------------------- BREADTH (bt)
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

    # ---------------------------------------------------------------- OI table (ot)
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

    # ---------------------------------------------------------------- 20 stocks list (ls)
    gs = o.gs
    LS = []
    for i in range(10):
        a, b2 = gs[i], gs[i + 10]
        LS.append((f"{a[0]} {a[1]:.1f}%", fmtG(a[2]), colG(a[2], fl), f"{b2[0]} {b2[1]:.1f}%", fmtG(b2[2]), colG(b2[2], fl)))
    tabs.append(T("STOCKS", C.posLs, LS, cols=4, enabled=C.showList))

    # ---------------------------------------------------------------- SECTOR (scT / scA)
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
    tabs.append(T("SECTOR ALL", C.scPosA, SA, enabled=C.sc
