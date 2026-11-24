\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.7in]{geometry}
\usepackage{listings}
\usepackage{xcolor}

\definecolor{codebg}{rgb}{0.96,0.96,0.96}
\definecolor{codegreen}{rgb}{0,0.5,0}
\definecolor{codegray}{rgb}{0.45,0.45,0.45}
\definecolor{codeblue}{rgb}{0.1,0.2,0.7}

\lstdefinestyle{pythonstyle}{
    backgroundcolor=\color{codebg},
    commentstyle=\color{codegreen},
    keywordstyle=\color{codeblue}\bfseries,
    numberstyle=\tiny\color{codegray},
    stringstyle=\color{red!70!black},
    basicstyle=\ttfamily\footnotesize,
    breaklines=true,
    numbers=left,
    numbersep=6pt,
    showstringspaces=false,
    tabsize=4,
    frame=single
}

\title{\textbf{NIFTY 50 Option Algo Full Code (Strict 09:15 AM -- 03:30 PM Dropdown Slots + Live Paper + Backtest)}}
\author{Amit K. -- Nifty Option Algo (`nifty-option-algo`)}
\date{\today}

\begin{document}
\maketitle

\section*{Key Improvements in Version 5}
\begin{itemize}
    \item \textbf{Bounded Market-Hours Dropdowns (\texttt{09:15 AM -- 03:30 PM IST}):} Ab 24-hour clock ki jagah sidebar mein \texttt{09:15 AM} se \texttt{03:30 PM} ke andar ke hi 5-minute time slots (jaise \texttt{09:15 AM}, \texttt{09:30 AM}, \texttt{10:00 AM} ... \texttt{03:20 PM}, \texttt{03:30 PM}) dropdown list mein dikhenge. Isse galti se bhi market hours ke bahar ka time select nahi ho payega.
    \item \textbf{Applied Across All Modes:} Yeh dropdown time selection \textbf{Live Real Trading}, \textbf{Live Paper Trading}, aur \textbf{Historical CSV Backtest} teeno par kaam karega.
    \item \textbf{Single vs. Multiple Trade Toggle:} Ek trade chalte hue dusra trade lena hai ya block karna hai, uska control bhi sidebar mein hai.
\end{itemize}

\section*{Complete Python Code (\texttt{app.py})}
\begin{lstlisting}[language=Python, style=pythonstyle]
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time as time_module
from datetime import datetime, time, timedelta
import pytz

# ==========================================
# PAGE CONFIGURATION & APP SETUP
# ==========================================
st.set_page_config(page_title="NIFTY 50 Option Algo (09:15 AM - 03:30 PM IST)", layout="wide")
st.title("NIFTY 50 Options Algo Trading (Live, Live Paper & Backtest)")

IST = pytz.timezone("Asia/Kolkata")

# ==========================================
# GENERATE 5-MIN TIME SLOTS (09:15 AM TO 03:30 PM)
# ==========================================
def generate_market_time_slots():
    """
    Generates exact 5-minute interval time objects strictly from 09:15 AM to 03:30 PM IST.
    """
    slots = []
    curr = datetime(2026, 1, 1, 9, 15)
    end = datetime(2026, 1, 1, 15, 30)
    while curr <= end:
        slots.append(curr.time())
        curr += timedelta(minutes=5)
    return slots

MARKET_SLOTS = generate_market_time_slots()

def format_time_12h(t_obj):
    return datetime.combine(datetime.today(), t_obj).strftime("%I:%M %p")

# ==========================================
# INITIALIZE SESSION STATE FOR TRADES
# ==========================================
if "completed_trades" not in st.session_state:
    st.session_state.completed_trades = []
if "active_positions" not in st.session_state:
    st.session_state.active_positions = []
if "last_signal_candle" not in st.session_state:
    st.session_state.last_signal_candle = None

# ==========================================
# STRICT MARKET HOURS & TIMEZONE FILTER
# ==========================================
def get_ist_now():
    return datetime.now(IST)

def is_valid_market_time(dt_obj, start_time, end_time):
    """
    Ensures trades/signals ONLY occur on Weekdays (Mon-Fri)
    strictly within the user-selected 09:15 AM - 03:30 PM IST window.
    """
    if dt_obj.tzinfo is None:
        dt_obj = IST.localize(dt_obj)
    else:
        dt_obj = dt_obj.astimezone(IST)

    # Monday = 0, Friday = 4 | Saturday = 5, Sunday = 6
    if dt_obj.weekday() >= 5:
        return False

    current_t = dt_obj.time()
    return start_time <= current_t <= end_time

# ==========================================
# TECHNICAL INDICATORS (DUAL HMA)
# ==========================================
def wma(series, period):
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def hma(series, period):
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = wma(series, half_length)
    wma_full = wma(series, period)
    diff = 2 * wma_half - wma_full
    return wma(diff, sqrt_length)

def compute_indicators(df, fast_hma_len=9, slow_hma_len=21):
    df = df.copy()
    df["HMA_Fast"] = hma(df["Close"], fast_hma_len)
    df["HMA_Slow"] = hma(df["Close"], slow_hma_len)
    return df

# ==========================================
# STRIKE SELECTION (ATM / ITM-1)
# ==========================================
def get_option_strike(spot_price, signal_type, strike_mode="ATM", step=50):
    atm_strike = round(spot_price / step) * step
    if signal_type == "BUY_CE":
        strike = atm_strike if strike_mode == "ATM" else atm_strike - step
        return f"{int(strike)} CE"
    elif signal_type == "BUY_PE":
        strike = atm_strike if strike_mode == "ATM" else atm_strike + step
        return f"{int(strike)} PE"
    return ""

# ==========================================
# LIVE NIFTY 5-MIN DATA FETCHER (DHAN API)
# ==========================================
def fetch_live_nifty_5min(client_id, access_token):
    url = "https://api.dhan.co/v2/charts/intraday"
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }
    payload = {
        "securityId": "13",
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",
        "interval": "5",
        "oi": False
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        data = resp.json()
        if "timestamp" in data and len(data["timestamp"]) > 0:
            df = pd.DataFrame({
                "Time": [datetime.fromtimestamp(ts, tz=IST).strftime("%Y-%m-%d %H:%M") for ts in data["timestamp"]],
                "Open": data["open"],
                "High": data["high"],
                "Low": data["low"],
                "Close": data["close"]
            })
            return df, None
        return None, f"Dhan API Response: {data}"
    except Exception as e:
        return None, str(e)

# ==========================================
# TELEGRAM & DHAN API ORDER EXECUTION
# ==========================================
def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def execute_order(mode, client_id, access_token, security_id, transaction_type, qty, signal_info, tg_token, tg_chat_id):
    now_str = get_ist_now().strftime("%Y-%m-%d %I:%M:%S %p")
    if mode == "Live Paper Trading":
        msg = (
            f"馃摑 *[PAPER TRADE - {transaction_type}]*
"
            f"Time: `{now_str} IST`
"
            f"Signal: `{signal_info['Signal']}` | Strike: `{signal_info['Strike']}`
"
            f"Spot: `{signal_info['Spot']}` | Qty: `{qty}`
"
            f"Active Trades: `{len(st.session_state.active_positions)}`"
        )
        send_telegram_alert(tg_token, tg_chat_id, msg)
        return {"status": "PAPER_FILLED", "orderId": f"PAPER_{int(datetime.now().timestamp())}"}

    elif mode == "Live Real Trading":
        url = "https://api.dhan.co/v2/orders"
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json"
        }
        payload = {
            "dhanClientId": client_id,
            "transactionType": transaction_type,
            "exchangeSegment": "NSE_FNO",
            "productType": "INTRADAY",
            "orderType": "MARKET",
            "validity": "DAY",
            "securityId": str(security_id),
            "quantity": int(qty)
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            res_json = resp.json()
            msg = (
                f"馃殌 *[LIVE REAL TRADE - {transaction_type}]*
"
                f"Time: `{now_str} IST`
"
                f"Signal: `{signal_info['Signal']}` | Strike: `{signal_info['Strike']}`
"
                f"Spot: `{signal_info['Spot']}` | Qty: `{qty}`
"
                f"Broker Resp: `{res_json}`"
            )
            send_telegram_alert(tg_token, tg_chat_id, msg)
            return res_json
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

# ==========================================
# LIVE MARKET ENGINE (09:15 AM - 03:30 PM DROPDOWN WINDOW)
# ==========================================
def process_live_market_tick(
    df, mode, lot_size, t1_pts, sl_pts, pcr_val, sector_breadth,
    strike_mode, allow_multiple, max_open_trades,
    trade_start_t, trade_end_t, square_off_t,
    client_id, access_token, tg_token, tg_chat_id
):
    now_ist = get_ist_now()
    if not is_valid_market_time(now_ist, trade_start_t, trade_end_t):
        return (
            f"Outside Trading Window ({format_time_12h(trade_start_t)} - {format_time_12h(trade_end_t)} IST). "
            f"No live/paper orders allowed."
        )

    df = compute_indicators(df)
    if len(df) < 3:
        return "Not enough 5-min candles yet to calculate HMA."

    latest_idx = len(df) - 1
    prev_idx = len(df) - 2
    candle_time_str = str(df.loc[latest_idx, "Time"])
    current_spot = float(df.loc[latest_idx, "Close"])
    current_high = float(df.loc[latest_idx, "High"])
    current_low = float(df.loc[latest_idx, "Low"])

    status_notes = []

    # 1. Manage All Active Open Positions (T1, SL, or Custom Square-Off Time)
    remaining_positions = []
    for pos in st.session_state.active_positions:
        entry_spot = pos["Entry_Spot"]
        sig = pos["Signal"]
        fav_move = (current_high - entry_spot) if sig == "BUY_CE" else (entry_spot - current_low)
        adv_move = (current_low - entry_spot) if sig == "BUY_CE" else (entry_spot - current_high)

        exit_reason = None
        pts = 0.0

        if now_ist.time() >= square_off_t:
            raw_move = (current_spot - entry_spot) if sig == "BUY_CE" else (entry_spot - current_spot)
            pts = round(raw_move * 0.5, 2)
            exit_reason = f"TIME EXIT ({format_time_12h(square_off_t)})"
        elif fav_move * 0.5 >= t1_pts:
            pts = float(t1_pts)
            exit_reason = "WIN (T1)"
        elif adv_move * 0.5 <= -sl_pts:
            pts = float(-sl_pts)
            exit_reason = "LOSS (SL)"

        if exit_reason:
            pnl_inr = int(round(pts * lot_size))
            trade_record = {
                "Time": pos["Entry_Time"],
                "Exit_Time": now_ist.strftime("%Y-%m-%d %I:%M %p"),
                "Mode": mode,
                "Signal": sig,
                "Strike": pos["Strike"],
                "Spot": round(entry_spot, 2),
                "Exit_Spot": round(current_spot, 2),
                "Result": exit_reason,
                "Points": pts,
                "PnL (INR)": pnl_inr
            }
            st.session_state.completed_trades.append(trade_record)
            execute_order(mode, client_id, access_token, "0", "SELL", lot_size, trade_record, tg_token, tg_chat_id)
            status_notes.append(f"Closed {pos['Strike']} ({exit_reason}) | PnL: 鈧箋pnl_inr}")
        else:
            remaining_positions.append(pos)

    st.session_state.active_positions = remaining_positions

    # 2. Check User-Defined Concurrent Trade Permission
    open_count = len(st.session_state.active_positions)
    can_open_new = (open_count == 0) if not allow_multiple else (open_count < max_open_trades)

    # 3. Evaluate New Signal on Current Candle (Only before square-off time)
    if st.session_state.last_signal_candle != candle_time_str and now_ist.time() < square_off_t:
        prev_fast = df.loc[prev_idx, "HMA_Fast"]
        prev_slow = df.loc[prev_idx, "HMA_Slow"]
        curr_fast = df.loc[latest_idx, "HMA_Fast"]
        curr_slow = df.loc[latest_idx, "HMA_Slow"]

        if not (pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow)):
            signal = None
            if prev_fast <= prev_slow and curr_fast > curr_slow and pcr_val >= 0.85 and sector_breadth >= -0.2:
                signal = "BUY_CE"
            elif prev_fast >= prev_slow and curr_fast < curr_slow and pcr_val <= 1.15 and sector_breadth <= 0.2:
                signal = "BUY_PE"

            if signal:
                st.session_state.last_signal_candle = candle_time_str
                if can_open_new:
                    strike_label = get_option_strike(current_spot, signal, strike_mode=strike_mode)
                    sig_info = {
                        "Entry_Time": now_ist.strftime("%Y-%m-%d %I:%M %p"),
                        "Signal": signal,
                        "Strike": strike_label,
                        "Spot": round(current_spot, 2),
                        "Entry_Spot": current_spot
                    }
                    st.session_state.active_positions.append(sig_info)
                    execute_order(mode, client_id, access_token, "0", "BUY", lot_size, sig_info, tg_token, tg_chat_id)
                    status_notes.append(f"New {mode} Entry: {signal} ({strike_label}) @ Spot {current_spot:.2f}")
                else:
                    status_notes.append(
                        f"Signal {signal} Skipped: Already {open_count} trade(s) active."
                    )

    if status_notes:
        return " | ".join(status_notes)

    return (
        f"Monitoring Live @ {now_ist.strftime('%I:%M:%S %p')} IST | Spot: {current_spot:.2f} | "
        f"Open Trades: {len(st.session_state.active_positions)}"
    )

# ==========================================
# HISTORICAL BACKTEST ENGINE (09:15 AM - 03:30 PM DROPDOWN WINDOW)
# ==========================================
def run_historical_backtest(
    df, lot_size=75, t1_pts=30, sl_pts=20, pcr_val=1.0,
    sector_breadth=0.0, strike_mode="ATM", allow_multiple=False, max_open_trades=3,
    trade_start_t=time(9, 15), trade_end_t=time(15, 30), square_off_t=time(15, 20)
):
    df = compute_indicators(df)
    trades = []
    active_until_idx = []

    for i in range(1, len(df)):
        row_time = pd.to_datetime(df.loc[i, "Time"])
        if not is_valid_market_time(row_time, trade_start_t, trade_end_t):
            continue

        if row_time.time() >= square_off_t:
            continue

        active_until_idx = [end_i for end_i in active_until_idx if end_i > i]
        can_enter = (len(active_until_idx) == 0) if not allow_multiple else (len(active_until_idx) < max_open_trades)

        if not can_enter:
            continue

        prev_fast = df.loc[i - 1, "HMA_Fast"]
        prev_slow = df.loc[i - 1, "HMA_Slow"]
        curr_fast = df.loc[i, "HMA_Fast"]
        curr_slow = df.loc[i, "HMA_Slow"]
        spot = df.loc[i, "Close"]

        if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
            continue

        signal = None
        if prev_fast <= prev_slow and curr_fast > curr_slow and pcr_val >= 0.85 and sector_breadth >= -0.2:
            signal = "BUY_CE"
        elif prev_fast >= prev_slow and curr_fast < curr_slow and pcr_val <= 1.15 and sector_breadth <= 0.2:
            signal = "BUY_PE"

        if signal:
            strike_label = get_option_strike(spot, signal, strike_mode=strike_mode)
            outcome = "OPEN"
            pts = 0
            exit_idx = len(df) - 1

            for j in range(i + 1, len(df)):
                future_time = pd.to_datetime(df.loc[j, "Time"])
                if future_time.date() != row_time.date() or future_time.time() >= square_off_t:
                    move = (df.loc[j - 1, "Close"] - spot) if signal == "BUY_CE" else (spot - df.loc[j - 1, "Close"])
                    pts = round(move * 0.5, 2)
                    outcome = f"TIME EXIT ({format_time_12h(square_off_t)})"
                    exit_idx = j
                    break

                high_diff = (df.loc[j, "High"] - spot) if signal == "BUY_CE" else (spot - df.loc[j, "Low"])
                low_diff = (df.loc[j, "Low"] - spot) if signal == "BUY_CE" else (spot - df.loc[j, "High"])

                if high_diff * 0.5 >= t1_pts:
                    outcome = "WIN (T1)"
                    pts = t1_pts
                    exit_idx = j
                    break
                elif low_diff * 0.5 <= -sl_pts:
                    outcome = "LOSS (SL)"
                    pts = -sl_pts
                    exit_idx = j
                    break

            active_until_idx.append(exit_idx)
            pnl_inr = int(round(pts * lot_size))
            trades.append({
                "Time": row_time.strftime("%Y-%m-%d %I:%M %p"),
                "Signal": signal,
                "Strike": strike_label,
                "Spot": round(spot, 2),
                "Result": outcome,
                "Points": pts,
                "PnL (INR)": pnl_inr
            })

    return pd.DataFrame(trades)

# ==========================================
# STREAMLIT SIDEBAR & UI CONTROLS
# ==========================================
with st.sidebar:
    st.header("1. Execution Mode")
    execution_mode = st.radio(
        "Select Trading Mode",
        ["Live Paper Trading", "Live Real Trading", "Historical Backtest (CSV)"],
        index=0
    )

    st.header("2. Market Time Window (Strictly 09:15 AM - 03:30 PM)")
    # Dropdowns strictly bounded between 09:15 AM and 03:30 PM in 5-min steps
    trade_start_time = st.selectbox(
        "Entry Start Time (09:15 AM - 03:30 PM)",
        options=MARKET_SLOTS[:-1],
        index=0,  # Default: 09:15 AM
        format_func=format_time_12h
    )
    valid_end_slots = [t for t in MARKET_SLOTS if t > trade_start_time]
    trade_end_time = st.selectbox(
        "Market Session End Time (Up to 03:30 PM)",
        options=valid_end_slots,
        index=len(valid_end_slots) - 1,  # Default: 03:30 PM
        format_func=format_time_12h
    )
    valid_sq_slots = [t for t in MARKET_SLOTS if trade_start_time < t <= trade_end_time]
    default_sq_idx = valid_sq_slots.index(time(15, 20)) if time(15, 20) in valid_sq_slots else len(valid_sq_slots) - 1
    auto_sq_off_time = st.selectbox(
        "Auto Square-Off Time (Inside Window)",
        options=valid_sq_slots,
        index=default_sq_idx,  # Default: 03:20 PM
        format_func=format_time_12h
    )

    st.header("3. Broker & Telegram Credentials")
    dhan_client_id = st.text_input("Dhan Client ID", value=st.secrets.get("DHAN_CLIENT_ID", ""))
    dhan_access_token = st.text_input("Daily Dhan Access Token", type="password")
    tg_token = st.text_input("Telegram Bot Token", value=st.secrets.get("TELEGRAM_TOKEN", ""), type="password")
    tg_chat_id = st.text_input("Telegram Chat ID", value=st.secrets.get("TELEGRAM_CHAT_ID", ""))

    st.header("4. Strategy & Concurrent Trade Control")
    allow_multiple_trades = st.checkbox(
        "Allow Multiple Concurrent Trades? (1 trade chalte hue dusra le ya nahi)",
        value=False
    )
    max_concurrent = st.number_input(
        "Max Concurrent Open Trades (If Allowed)",
        min_value=1, max_value=10, value=2,
        disabled=not allow_multiple_trades
    )
    strike_choice = st.selectbox("Strike Selection", ["ATM", "ITM-1"])
    lot_qty = st.number_input("Quantity (1 Lot = 75)", min_value=75, step=75, value=75)
    t1_target = st.number_input("Target 1 (Points)", min_value=5, value=30)
    sl_points = st.number_input("Stop Loss (Points)", min_value=5, value=20)

    st.header("5. OI & Sector Breadth Filters")
    vol_pcr = st.number_input("Live Volume PCR", value=1.02, step=0.05)
    sec_breadth = st.number_input("Sector Breadth Score (-1 to +1)", value=0.25, step=0.05)

now_ist = get_ist_now()
market_open = is_valid_market_time(now_ist, trade_start_time, trade_end_time)
window_str = f"{format_time_12h(trade_start_time)} - {format_time_12h(trade_end_time)} IST"
status_label = f"ACTIVE ({window_str})" if market_open else f"BLOCKED (Outside {window_str})"
trade_rule_label = f"Multi-Trade (Max {max_concurrent})" if allow_multiple_trades else "Single Trade Only"

st.info(
    f"IST Time: **{now_ist.strftime('%Y-%m-%d %I:%M:%S %p')}** | Window: **{status_label}** | "
    f"Sq-Off: **{format_time_12h(auto_sq_off_time)}** | Rule: **{trade_rule_label}**"
)

# ==========================================
# MODE 1 & 2: LIVE PAPER TRADING / LIVE REAL TRADING
# ==========================================
if execution_mode in ["Live Paper Trading", "Live Real Trading"]:
    st.subheader(f"{execution_mode} Dashboard ({window_str})")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        auto_refresh = st.checkbox("Auto-Refresh Live Market Feed (Every 15 Seconds)", value=False)
    with col_b:
        if st.button("Reset Active & Completed Trades"):
            st.session_state.completed_trades = []
            st.session_state.active_positions = []
            st.session_state.last_signal_candle = None
            st.success("Session reset.")

    if not dhan_client_id or not dhan_access_token:
        st.warning("Enter Dhan Client ID and Daily Access Token in the sidebar to fetch live 5-min NIFTY data.")
    else:
        live_df, err = fetch_live_nifty_5min(dhan_client_id, dhan_access_token)
        if err:
            st.error(f"Data Fetch Error: {err}")
        elif live_df is not None:
            status_msg = process_live_market_tick(
                live_df, execution_mode, lot_qty, t1_target, sl_points,
                vol_pcr, sec_breadth, strike_choice,
                allow_multiple_trades, max_concurrent,
                trade_start_time, trade_end_time, auto_sq_off_time,
                dhan_client_id, dhan_access_token, tg_token, tg_chat_id
            )
            st.success(status_msg)

            if st.session_state.active_positions:
                st.subheader(f"Active Open Positions ({len(st.session_state.active_positions)})")
                st.dataframe(pd.DataFrame(st.session_state.active_positions), use_container_width=True)

            if st.session_state.completed_trades:
                pt_df = pd.DataFrame(st.session_state.completed_trades)
                st.subheader(f"{execution_mode} Completed Trades Log")
                st.dataframe(pt_df, use_container_width=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Trades", len(pt_df))
                m2.metric("Win Rate", f"{(pt_df['Points'] > 0).mean()*100:.1f}%")
                m3.metric("Total PnL (INR)", f"鈧箋pt_df['PnL (INR)'].sum():,}")
                st.download_button(
                    "Download Live/Paper Trade Log CSV",
                    pt_df.to_csv(index=False).encode("utf-8"),
                    "nifty_live_paper_trades.csv",
                    "text/csv"
                )

    if auto_refresh:
        time_module.sleep(15)
        st.rerun()

# ==========================================
# MODE 3: HISTORICAL BACKTEST (CSV)
# ==========================================
else:
    st.subheader(f"Historical CSV Backtester ({window_str} Filtered)")
    uploaded_ohlc = st.file_uploader("Upload 5-Min NIFTY OHLC CSV (Columns: Time, Open, High, Low, Close)", type=["csv"])
    if uploaded_ohlc is not None:
        raw_df = pd.read_csv(uploaded_ohlc)
        results_df = run_historical_backtest(
            raw_df, lot_size=lot_qty, t1_pts=t1_target, sl_pts=sl_points,
            pcr_val=vol_pcr, sector_breadth=sec_breadth, strike_mode=strike_choice,
            allow_multiple=allow_multiple_trades, max_open_trades=max_concurrent,
            trade_start_t=trade_start_time, trade_end_t=trade_end_time, square_off_t=auto_sq_off_time
        )
        st.dataframe(results_df, use_container_width=True)
        if not results_df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Trades", len(results_df))
            c2.metric("Win Rate", f"{(results_df['Points'] > 0).mean()*100:.1f}%")
            c3.metric("Net PnL (INR)", f"鈧箋results_df['PnL (INR)'].sum():,}")
            st.download_button(
                "Download Clean Backtest CSV",
                results_df.to_csv().encode("utf-8"),
                "nifty_clean_backtest.csv",
                "text/csv"
            )

\end{lstlisting}

\end{document}
