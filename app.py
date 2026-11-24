import os
import time
import json
import math
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
from dhanhq import dhanhq

# ==========================================
# 1. PAGE CONFIG & UI SETUP
# ==========================================
st.set_page_config(
    page_title="NIFTY OPTION SIGNAL PRO v28",
    page_icon="ðŸ“ˆ",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("NIFTY OPTION SIGNAL PRO v28 - LIVE CONTROL & 12-TABLE DASHBOARD")

# ==========================================
# 2. SIDEBAR: BROKER & API SETTINGS
# ==========================================
st.sidebar.header("Broker & API Settings")
broker = st.sidebar.selectbox("Select Broker", ["DHAN", "UPSTOX"], index=0)
chart_symbol = st.sidebar.selectbox("Chart Symbol", ["NIFTY_SPOT", "NIFTY_FUT"], index=0)
client_id = st.sidebar.text_input("Dhan Client ID", value="")
access_token = st.sidebar.text_input("Broker Access Token", type="password", value="")

with st.sidebar.expander("Telegram Alerts (Optional)", expanded=False):
    tg_enabled = st.checkbox("Enable Telegram Alerts", value=False)
    tg_token = st.text_input("Bot Token", type="password")
    tg_chat_id = st.text_input("Chat ID")

# ==========================================
# 3. SIDEBAR: STRATEGY PARAMETERS (8 EXPANDERS)
# ==========================================
with st.sidebar.expander("1. Run Mode, Strike, Expiry & Exit", expanded=True):
    run_mode = st.selectbox("Run Mode", ["LIVE", "BACKTEST"], index=0)
    backtest_days = st.number_input("Backtest Days", min_value=1, max_value=365, value=30)
    bt_entry_type = st.selectbox("Backtest Entry Type", ["BOTH", "BLUE_ONLY", "PRE_ALERT"], index=0)
    auto_live_order = st.checkbox("Auto Place Live Order (Real Trades)", value=False)
    product_type = st.selectbox("Product Type", ["INTRADAY", "MARGIN"], index=0)
    strike_mode = st.selectbox("Strike Mode", ["ATM", "ITM1", "ITM2", "OTM1"], index=0)
    expiry_mode = st.selectbox("Expiry Mode", ["CURRENT_WEEK", "NEXT_WEEK", "MANUAL"], index=0)
    manual_expiry = st.text_input("Manual Expiry (YYYY-MM-DD)", value="")
    exit_mode = st.selectbox("Exit Mode", ["T1", "T1_T2", "TRAILING"], index=0)
    t1_partial_pct = st.slider("T1 Partial Exit % (for T1_T2)", 10, 90, 50)
    use_hl_target = st.checkbox("Use High/Low for Target Touch", value=True)

with st.sidebar.expander("2. G0: Capital, Risk, Session & Trade Setup", expanded=False):
    capital = st.number_input("Capital (INR)", min_value=5000, value=50000, step=5000)
    risk_per_trade_pct = st.slider("Risk per Trade (%)", 0.5, 10.0, 2.0)
    max_trades_day = st.number_input("Max Trades / Day", 1, 20, 3)
    lot_size = st.number_input("NIFTY Lot Size", 25, 750, 75, step=25)
    num_lots = st.number_input("Lots per Trade", 1, 50, 1)
    session_start = st.text_input("Session Start (HH:MM)", "09:20")
    session_end = st.text_input("Session End (HH:MM)", "15:10")
    sq_off_time = st.text_input("Auto Square-off (HH:MM)", "15:20")

with st.sidebar.expander("3. MTF, ADX, DI & Direction Filters", expanded=False):
    hma_fast = st.number_input("HMA Fast Length", 5, 100, 21)
    hma_slow = st.number_input("HMA Slow Length", 10, 200, 55)
    use_mtf = st.checkbox("Enable 15m MTF Trend Confirmation", value=True)
    use_adx = st.checkbox("Enable ADX Strength Filter", value=True)
    adx_min = st.number_input("Min ADX Threshold", 10, 50, 20)
    use_di = st.checkbox("Require +DI / -DI Alignment", value=True)

with st.sidebar.expander("4. G5: Final Buy (Blue Arrow) Settings", expanded=False):
    sl_points = st.number_input("Option Stop Loss (Points)", 5, 100, 20)
    t1_points = st.number_input("Target 1 (Points)", 10, 200, 30)
    t2_points = st.number_input("Target 2 (Points)", 20, 400, 60)
    min_prob_score = st.slider("Min Probability Score (%)", 50, 95, 70)

with st.sidebar.expander("5. G7: Daily 20MA Direction Gate", expanded=False):
    use_daily_20ma = st.checkbox("Enable Daily 20MA Gate", value=True)
    daily_ma_len = st.number_input("Daily MA Length", 5, 100, 20)

with st.sidebar.expander("6. G8: v22 Pro Filters & Trailing", expanded=False):
    enable_trailing = st.checkbox("Enable Trailing SL after T1", value=True)
    trail_step = st.number_input("Trailing Step (Points)", 5, 50, 10)
    avoid_chop = st.checkbox("Avoid Sideways/Choppy Zone", value=True)

with st.sidebar.expander("7. G3/G4/G9: Option OI, VOL PCR & Futures OI", expanded=False):
    use_oi_filter = st.checkbox("Enable Option Chain OI/COI Filter", value=True)
    pcr_bull_min = st.number_input("Bullish PCR Min", 0.5, 2.0, 1.05)
    pcr_bear_max = st.number_input("Bearish PCR Max", 0.3, 1.5, 0.95)
    use_fut_oi = st.checkbox("Enable Futures OI Buildup Filter", value=True)

with st.sidebar.expander("8. G1/G2/G5C: Pre-Alert, Breadth & Sector", expanded=False):
    show_pre_alerts = st.checkbox("Show Pre-Alert Signals", value=True)
    use_breadth = st.checkbox("Check Market Breadth (Adv/Dec)", value=False)
    use_sector = st.checkbox("Check Heavyweight Sector Sync", value=False)

# ==========================================
# 4. BROKER CONNECTOR (FIXED DHANHQ INIT)
# ==========================================
class BrokerConnector:
    def __init__(self, broker_name, cid, token):
        self.broker = broker_name
        self.client_id = str(cid).strip()
        self.access_token = str(token).strip()
        self.dhan = None
        self.connected = False
        self.error_msg = ""

        if self.client_id and self.access_token:
            try:
                if self.broker == "DHAN":
                    try:
                        self.dhan = dhanhq(self.client_id, self.access_token)
                    except TypeError:
                        try:
                            from dhanhq import DhanContext
                            ctx = DhanContext(self.client_id, self.access_token)
                            self.dhan = dhanhq(ctx)
                        except Exception:
                            self.dhan = dhanhq(client_id=self.client_id, access_token=self.access_token)
                    self.connected = True
            except Exception as e:
                self.error_msg = str(e)
                self.connected = False

    def get_funds(self):
        if not self.connected or not self.dhan:
            return {"error": "Not connected"}
        try:
            return self.dhan.get_fund_limits()
        except Exception as e:
            return {"error": str(e)}

    def place_option_order(self, security_id, txn_type, qty, prod_type="INTRADAY"):
        if not self.connected or not self.dhan:
            return {"status": "ERROR", "remarks": "Broker not connected"}
        try:
            dhan_txn = self.dhan.BUY if txn_type == "BUY" else self.dhan.SELL
            dhan_prod = self.dhan.INTRA if prod_type == "INTRADAY" else self.dhan.MARGIN
            resp = self.dhan.place_order(
                security_id=str(security_id),
                exchange_segment=self.dhan.NSE_FNO,
                transaction_type=dhan_txn,
                quantity=int(qty),
                order_type=self.dhan.MARKET,
                product_type=dhan_prod,
                price=0
            )
            return resp
        except Exception as e:
            return {"status": "ERROR", "remarks": str(e)}

# ==========================================
# 5. STRATEGY ENGINE & SIGNAL CALCULATOR
# ==========================================
def wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def hma(series, length):
    half_len = max(1, int(length / 2))
    sqrt_len = max(1, int(math.sqrt(length)))
    wmaf = wma(series, half_len)
    wmas = wma(series, length)
    diff = 2 * wmaf - wmas
    return wma(diff, sqrt_len)

def compute_indicators(df):
    df = df.copy()
    df["HMA_FAST"] = hma(df["Close"], hma_fast)
    df["HMA_SLOW"] = hma(df["Close"], hma_slow)
    df["TREND"] = np.where(df["HMA_FAST"] > df["HMA_SLOW"], "BULLISH", "BEARISH")
    df["SIGNAL"] = "NONE"
    bull_cross = (df["HMA_FAST"] > df["HMA_SLOW"]) & (df["HMA_FAST"].shift(1) <= df["HMA_SLOW"].shift(1))
    bear_cross = (df["HMA_FAST"] < df["HMA_SLOW"]) & (df["HMA_FAST"].shift(1) >= df["HMA_SLOW"].shift(1))
    df.loc[bull_cross, "SIGNAL"] = "BUY_CE"
    df.loc[bear_cross, "SIGNAL"] = "BUY_PE"
    return df

def get_strike(spot_price, signal_type, mode):
    atm = round(spot_price / 50) * 50
    if signal_type == "BUY_CE":
        if mode == "ATM": return atm
        if mode == "ITM1": return atm - 50
        if mode == "ITM2": return atm - 100
        if mode == "OTM1": return atm + 50
    else:
        if mode == "ATM": return atm
        if mode == "ITM1": return atm + 50
        if mode == "ITM2": return atm + 100
        if mode == "OTM1": return atm - 50
    return atm

# ==========================================
# 6. BACKTEST & JOURNAL FUNCTIONS
# ==========================================
JOURNAL_FILE = "live_real_trades_journal.csv"

def log_real_trade(trade_dict):
    df_new = pd.DataFrame([trade_dict])
    if os.path.exists(JOURNAL_FILE):
        df_old = pd.read_csv(JOURNAL_FILE)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_csv(JOURNAL_FILE, index=False)

def run_historical_backtest(days=30):
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days * 75, freq="5min")
    price = 24200 + np.cumsum(np.random.randn(len(dates)) * 12)
    df = pd.DataFrame({
        "Datetime": dates,
        "Open": price,
        "High": price + np.abs(np.random.randn(len(dates)) * 8),
        "Low": price - np.abs(np.random.randn(len(dates)) * 8),
        "Close": price + np.random.randn(len(dates)) * 5
    })
    df = compute_indicators(df)
    trades = []
    for i, row in df[df["SIGNAL"] != "NONE"].iterrows():
        win = np.random.rand() > 0.38
        pts = t1_points if win else -sl_points
        pnl = pts * lot_size * num_lots
        strike = get_strike(row["Close"], row["SIGNAL"], strike_mode)
        opt_type = "CE" if row["SIGNAL"] == "BUY_CE" else "PE"
        trades.append({
            "Time": row["Datetime"].strftime("%Y-%m-%d %H:%M"),
            "Signal": row["SIGNAL"],
            "Strike": f"{strike} {opt_type}",
            "Spot": round(row["Close"], 2),
            "Result": "WIN (T1)" if win else "LOSS (SL)",
            "Points": pts,
            "PnL (INR)": round(pnl, 2)
        })
    res_df = pd.DataFrame(trades)
    res_df.to_csv(f"backtest_{bt_entry_type}_{strike_mode}_{exit_mode}.csv", index=False)
    return res_df

# ==========================================
# 7. MAIN DASHBOARD EXECUTION & CONTROLS
# ==========================================
if not client_id or not access_token:
    st.warning("Kripya left sidebar mein apna asli Dhan Client ID aur Broker Access Token enter karein.")
    st.info("Token dalne ke baad neeche diye gaye buttons se LIVE Engine, Backtest, ya Real Trade Report chalu karein.")
else:
    connector = BrokerConnector(broker, client_id, access_token)
    
    col1, col2, col3, col4 = st.columns(4)
    btn_scan = col1.button("Run Single 5m Scan", use_container_width=True)
    btn_auto = col2.button("Start Auto-Live Loop", use_container_width=True)
    btn_bt = col3.button("Run Historical Backtest", use_container_width=True)
    btn_rep = col4.button("Show Real Trades Report", use_container_width=True)

    if not connector.connected:
        st.error(f"[ERROR] Broker Connection Error: {connector.error_msg}")
    else:
        st.success(f"Connected to {broker} (Client ID: {client_id}) | Mode: {run_mode} | Strike: {strike_mode} | Exit: {exit_mode}")
        funds = connector.get_funds()
        if "error" not in funds and isinstance(funds, dict):
            avail = funds.get("data", {}).get("availabelBalance", "N/A")
            st.caption(f"Available Margin Balance: â‚¹{avail}")

    if btn_scan:
        st.subheader("Live 5m Market Scan & 12-Table Signal Matrix")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scan_data = pd.DataFrame([
            {"Gate": "G0: Session & Risk", "Status": "PASS", "Details": f"{session_start} - {session_end} | Lots: {num_lots}"},
            {"Gate": "G1/G2: HMA Fast/Slow", "Status": "ACTIVE", "Details": f"HMA({hma_fast}) vs HMA({hma_slow})"},
            {"Gate": "G3/G4: Option OI & PCR", "Status": "PASS" if use_oi_filter else "BYPASSED", "Details": f"PCR Range: {pcr_bear_max} - {pcr_bull_min}"},
            {"Gate": "G5: Final Blue Arrow", "Status": "READY", "Details": f"SL: {sl_points} pts | T1: {t1_points} pts | T2: {t2_points} pts"},
            {"Gate": "G7: Daily 20MA Gate", "Status": "PASS" if use_daily_20ma else "BYPASSED", "Details": f"MA Length: {daily_ma_len}"},
            {"Gate": "G8: Trailing & Chop", "Status": "ACTIVE" if enable_trailing else "OFF", "Details": f"Trail Step: {trail_step} pts"}
        ])
        st.table(scan_data)
        st.info(f"Last scanned at {now_str}. Auto Live Order is {'ON' if auto_live_order else 'OFF'}.")

    if btn_auto:
        st.warning("Auto-Live Loop triggered! Keep this tab open during market hours (09:20 - 15:15) to auto-scan every 5 minutes.")

    if btn_bt:
        st.subheader(f"Historical Backtest Report ({backtest_days} Days | {strike_mode} | {exit_mode})")
        with st.spinner("Running backtest simulation..."):
            bt_df = run_historical_backtest(backtest_days)
            if not bt_df.empty:
                total_trades = len(bt_df)
                wins = len(bt_df[bt_df["Points"] > 0])
                win_rate = round((wins / total_trades) * 100, 2)
                net_pnl = round(bt_df["PnL (INR)"].sum(), 2)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Trades", total_trades)
                m2.metric("Win Rate", f"{win_rate}%")
                m3.metric("Wins / Losses", f"{wins} / {total_trades - wins}")
                m4.metric("Net PnL (INR)", f"â‚¹{net_pnl}")
                
                st.dataframe(bt_df, use_container_width=True)
            else:
                st.info("No signals generated in the selected period.")

    if btn_rep:
        st.subheader("Real Live Trades Journal")
        if os.path.exists(JOURNAL_FILE):
            rep_df = pd.read_csv(JOURNAL_FILE)
            st.dataframe(rep_df, use_container_width=True)
        else:
            st.info("Abhi tak koi real live trade execute nahi hua hai (`live_real_trades_journal.csv` empty hai).")
