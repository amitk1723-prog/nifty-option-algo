import os
import time
import math
import datetime as dt
import pytz
import requests
import pandas as pd
import numpy as np

# ==============================================================================
# 1. BROKER, CHART, EXECUTION & TELEGRAM CONFIG (GitHub Secrets + Direct Support)
# ==============================================================================
CONFIG = {
    "BROKER": os.environ.get("BROKER", "DHAN"),              # "DHAN" ya "UPSTOX"
    "CHART_SYMBOL": os.environ.get("CHART_SYMBOL", "NIFTY_SPOT"),  # "NIFTY_SPOT" ya "NIFTY_FUT"

    # Dhan API Credentials (Direct paste karein ya GitHub Secrets se auto-load hoga)
    "DHAN_CLIENT_ID": os.environ.get("DHAN_CLIENT_ID", "YOUR_DHAN_CLIENT_ID"),
    "DHAN_ACCESS_TOKEN": os.environ.get("DHAN_ACCESS_TOKEN", "YOUR_DHAN_ACCESS_TOKEN"),

    # Upstox API Credentials
    "UPSTOX_ACCESS_TOKEN": os.environ.get("UPSTOX_ACCESS_TOKEN", "YOUR_UPSTOX_ACCESS_TOKEN"),

    # Telegram Alerts (Optional)
    "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),

    # Run Mode & Order Execution
    "RUN_MODE": "LIVE",            # "LIVE" = Real-time Market Algo | "BACKTEST" = Historical Backtest
    "BACKTEST_DAYS": 30,           # Backtest kitne din ke historical data par chalana hai
    "BACKTEST_ENTRY_TYPE": "BOTH", # "ALL_SIGNALS" | "REAL_BLUE_ONLY" | "BOTH"
    "AUTO_PLACE_ORDER": False,     # True = Blue Arrow par Live Order jayega | False = Sirf Alert/Log
    "PRODUCT_TYPE": "INTRADAY",
    "INTERACTIVE_MENU": True,      # True = Run karte hi screen par Option Selection Menu aayega
    "REAL_TRADES_CSV": "live_real_trades_journal.csv",  # Real Live Trades ka permanent record file
}

# ==============================================================================
# 2. COMPLETE INDICATOR SETTINGS (100% EXACT PINE SCRIPT v28 + VOL PCR)
# ==============================================================================
PARAMS = {
    # --- STRIKE & EXPIRY SELECTION OPTIONS ---
    "strikeMode": "ATM",           # Options: "ATM", "ITM_1", "ITM_2", "OTM_1"
    "expiryMode": "CURRENT_WEEK",  # Options: "CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"
    "manualExpiry": "",            # Sirf expiryMode="MANUAL" ke liye (e.g., "2026-11-24")

    # --- TARGET EXIT OPTIONS (Live Algo + Backtest Dono Ke Liye) ---
    "exitMode": "T1",              # Options: "T1", "T2", "T1_T2", "MANUAL"
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
    "ocN": 4,                      # Option OI ke liye ATM +- N strikes (Options: 2,3,4,5,6,7,8,9)
    "pcrIn": 0.0,                  # Manual OI PCR (0 = OFF)
    "callWall": 0.0,               # Manual Call Wall (0 = OFF)
    "putWall": 0.0,                # Manual Put Wall (0 = OFF)
    "wallBuf": 0.3,                # Wall ke itne % paas aane par us side ka trade skip
    "pcrBull": 1.1,
    "pcrBear": 0.9,

    "ovOn": True,                  # VOL PCR indicator ON/OFF
    "ovN": 5,                      # Option Volume ke liye ATM +- N strikes (Options: 2,3,4,5,6,7,8,9)
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

            elif self.broker == "UPSTOX":
                res = requests.get(
                    f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={selected_exp}",
                    headers=self.headers, timeout=10
                ).json()
                for row in res.get("data", []):
                    k = row.get("strike_price", 0)
                    c_md = row.get("call_options", {}).get("market_data", {})
                    p_md = row.get("put_options", {}).get("market_data", {})

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
            "expiry": selected_exp,
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

        # Real Live Trade Counter (Kitne Real Trade Algo Ne Liye)
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
            "Contract": f"NIFTY {int(strike)} {side}",
            "StrikeMode": PARAMS["strikeMode"],
            "Expiry": expiry,
            "Lots": lots,
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
                    df_all.loc[mask, "ExitTime"] = exit_ts.strftime("%H:%M:%S")
                    df_all.loc[mask, "ExitSpot"] = round(exit_px, 2)
                    df_all.loc[mask, "ExitReason"] = exit_reason
                    df_all.loc[mask, "PnL_Pts"] = round(pnl_pts, 2)
                    df_all.loc[mask, "Status"] = "CLOSED"
                    df_all.to_csv(csv_file, index=False)
            except Exception:
                pass
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

        if self.remainingLots > 0:
            self.broker.place_option_order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)

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
        self.trade_journal.append({
            "EntryTime": self.entT.strftime("%Y-%m-%d %H:%M") if self.entT else "",
            "ExitTime": exit_ts.strftime("%Y-%m-%d %H:%M"),
            "Signal": self.entTx,
            "Strike": f"{int(self.activeStrike)} ({PARAMS['strikeMode']})",
            "Expiry": self.activeExpiry,
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

        self._log_real_trade_exit(exit_ts, exit_px, exit_reason, pnl_pts)
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
            "vwap": v, "vwOk": vwOk, "orTxt": orTxt,
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
            "secAvg": sec_avg, "scBk": scBk, "scCE": scCE, "scPE": scPE
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

        # G8 (v22 Upgrades) Evaluation
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
            return

        # ======================================================================
        # EXIT LOGIC: T1, T2, T1_T2 (PARTIAL), MANUAL, SL, SUPERTREND, TIME
        # ======================================================================
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
            self.t1Booked = True
            self.posSl = self.posEn
            self.posMv = True
            side_str = "CE" if self.posSt == 1 else "PE"
            self.broker.place_option_order(side_str, self.activeStrike, lots_to_book, action="SELL", expiry_date=self.activeExpiry)
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

            if self.remainingLots > 0:
                self.broker.place_option_order(side_str, self.activeStrike, self.remainingLots, action="SELL", expiry_date=self.activeExpiry)

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

        # STEP 1: INITIAL SIGNAL (GREEN / RED ARROW) -> WATCH START
        fb_msg = "-- | " + self.wLast
        if entCE or entPE:
            lvS = 1 if entCE else -1
            side_lbl = "CE" if entCE else "PE"
            arrow_icon = "[GREEN ARROW]" if entCE else "[RED ARROW]"
            ent_prob = probCE if entCE else probPE
            chosen_strike = strikeCE if entCE else strikePE
            init_sl = close - lvS * slD

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
                order_ok = self.broker.place_option_order(side_lbl, chosen_strike, lots, action="BUY", expiry_date=selected_exp)
                self._log_real_trade_entry(bar_ts, side_lbl, chosen_strike, selected_exp, lots, close, ent_prob, order_ok)

            self.alert(
                f"{arrow_icon} STEP 1: INITIAL {side_lbl} SIGNAL ({fin}) @ {close:.1f} | Prob: {ent_prob:.0f}%\n"
                f"Strike: {int(chosen_strike)} {side_lbl} ({PARAMS['strikeMode']}) | Expiry: {selected_exp} ({PARAMS['expiryMode']})\n"
                f"WATCH MODE ON - Final Buy (Blue Arrow) ki calculation chal rahi hai...\n"
                f"Exit Mode: {exit_mode} | SL: {init_sl:.1f} | T1: {close + lvS * slD * PARAMS['rrT']:.1f} | T2: {close + lvS * slD * (PARAMS['rrT'] + 1.0):.1f}"
            )

        # STEP 2 & 3: CALCULATION -> FINAL BUY TRADE (BLUE ARROW)
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

                    order_ok = self.broker.place_option_order(fb_side, self.activeStrike, self.activeLots, action="BUY", expiry_date=self.activeExpiry)
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
        atmNow = round(close / PARAMS["optStep"]) * PARAMS["optStep"]
        if self.ovCtr is None and atmNow > 0:
            self.ovCtr = atmNow

        oc_data = self.broker.get_option_chain_metrics(
            atmNow, self.ovCtr, PARAMS["ocN"], PARAMS["ovN"]
        ) if (PARAMS["autoOc"] or PARAMS["ovOn"]) else {}

        stock_changes = self.broker.get_breadth_changes()
        self.evaluate_bar_data(df_5m, df_3m, df_15m, df_1h, df_4h, df_d, df_fut, df_vix, stock_changes, oc_data, is_pre_alert=is_pre_alert)


# ==============================================================================
# 6. HISTORICAL BACKTEST RUNNER (ALL SIGNALS + REAL BLUE ARROW TRADE ON SAME DATA)
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
        print("Backtest ke liye paryapt historical data nahi mila.")
        return

    stock_daily = {}
    for sym, _ in BREADTH_STOCKS:
        d_s = broker.get_candles(sym, interval="D", days=days + 15)
        if not d_s.empty:
            d_s["pct"] = d_s["close"].pct_change() * 100.0
            stock_daily[sym] = d_s["pct"]

    modes_to_run = ["ALL_SIGNALS", "REAL_BLUE_ONLY"] if bt_type == "BOTH" else [bt_type]

    for mode_label in modes_to_run:
        engine = NiftyOptionProEngine(broker, is_backtest=True, bt_entry_mode=mode_label)
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

        total_trades = engine.winN + engine.lossN
        win_rate = (engine.winN / total_trades * 100.0) if total_trades > 0 else 0.0
        pf = (engine.gp / engine.gl) if engine.gl > 0 else (float("inf") if engine.gp > 0 else 0.0)

        title_tag = "REAL TRADE BACKTEST (BLUE ARROW FINAL BUY ONLY)" if mode_label == "REAL_BLUE_ONLY" else "INITIAL SIGNALS BACKTEST (GREEN/RED ARROW)"
        print("\n" + "=" * 92)
        print(f"{title_tag}")
        print(f"Strike: {PARAMS['strikeMode']} | Expiry: {PARAMS['expiryMode']} | Exit: {PARAMS['exitMode']} | Total Trades: {total_trades}")
        print(f"Wins: {engine.winN} | Losses: {engine.lossN} | Win%: {win_rate:.1f}% | Profit Factor: {pf:.2f}")
        print(f"Total Net Points: {engine.totPnl:+.2f} pts | Max Drawdown: -{engine.maxDD:.2f} pts")
        print("=" * 92)

        if engine.trade_journal:
            j_df = pd.DataFrame(engine.trade_journal)
            print(j_df.to_string(index=False))
            csv_name = f"backtest_{mode_label}_{PARAMS['strikeMode']}_{PARAMS['exitMode']}.csv"
            j_df.to_csv(csv_name, index=False)
            print(f"\nTrade Journal saved to: {csv_name}")


# ==============================================================================
# 7. MAIN ENTRYPOINT (INTERACTIVE OPTION SELECTOR + LIVE ALGO / BACKTEST)
# ==============================================================================
if __name__ == "__main__":
    connector = BrokerConnector(CONFIG)
    interactive_option_selector(connector)

    if CONFIG["RUN_MODE"].upper() == "BACKTEST":
        run_backtest(connector, days=CONFIG["BACKTEST_DAYS"])
    else:
        print(f"Starting LIVE Nifty Option Signal PRO v28 | Strike: {PARAMS['strikeMode']} | Expiry: {PARAMS['expiryMode']} | Exit: {PARAMS['exitMode']}...")
        engine = NiftyOptionProEngine(connector, is_backtest=False)
        print(f"Ab Tak Liye Gaye Total Real Trades: {engine.real_trade_count} (Live Broker Orders: {engine.real_live_orders_sent})")
        print("TIP: Kisi bhi samay manual exit lene ya Real Trade Report dekhne ke liye Ctrl+C dabayein.")

        try:
            while True:
                now = dt.datetime.now(IST)
                if PARAMS["preSec"] > 0 and (now.minute % 5 == 4) and (now.second == 60 - PARAMS["preSec"]):
                    try:
                        engine.process_live_bar(is_pre_alert=True)
                    except Exception:
                        pass
                    time.sleep(1)

                if (now.minute % 5 == 0) and (now.second == 2):
                    try:
                        engine.process_live_bar(is_pre_alert=False)
                    except Exception as exc:
                        print(f"[Error] {exc}")
                    time.sleep(2)

                time.sleep(0.5)
        except KeyboardInterrupt:
            if engine.posSt != 0:
                ans = input("\nActive trade chal raha hai! Kya abhi MANUAL EXIT lena hai? (y/n): ").strip().lower()
                if ans == "y":
                    df_now = connector.get_candles(CONFIG["CHART_SYMBOL"], interval="5", days=1)
                    if not df_now.empty:
                        engine.manual_exit_now(df_now["close"].iloc[-1], dt.datetime.now(IST), reason="MANUAL_EXIT")
            show_real_trade_report(connector)
            print("Algo stopped safely.")
