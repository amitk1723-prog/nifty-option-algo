import os
import time
import threading
import datetime as dt
import pandas as pd
import streamlit as st

# NOTE: Agar aapki main python file ka naam 'main.py' ke alawa kuch aur hai (jaise algo.py),
# toh neeche 'import main as algo' ko badal kar 'import algo as algo' kar dein.
import main as algo

st.set_page_config(page_title="Nifty Algo Control Panel", page_icon="📈", layout="wide")

# Background Engine State (Taaki browser refresh karne par bhi algo chalta rahe)
@st.cache_resource
def get_engine_state():
    return {
        "running": False,
        "thread": None,
        "engine": None,
        "connector": None,
        "status_msg": "Stopped (Band Hai)",
        "last_update": "--"
    }

state = get_engine_state()

def live_algo_loop():
    try:
        connector = algo.BrokerConnector(algo.CONFIG)
        engine = algo.NiftyOptionProEngine(connector, is_backtest=False)
        state["connector"] = connector
        state["engine"] = engine
        state["status_msg"] = "RUNNING (Live Market Monitoring ON)"

        while state["running"]:
            now = dt.datetime.now(algo.IST)
            state["last_update"] = now.strftime("%H:%M:%S IST")

            if algo.PARAMS["preSec"] > 0 and (now.minute % 5 == 4) and (now.second == 60 - algo.PARAMS["preSec"]):
                try:
                    engine.process_live_bar(is_pre_alert=True)
                except Exception:
                    pass
                time.sleep(1)

            if (now.minute % 5 == 0) and (now.second == 2):
                try:
                    engine.process_live_bar(is_pre_alert=False)
                except Exception as exc:
                    state["status_msg"] = f"Error: {exc}"
                time.sleep(2)

            time.sleep(0.5)
    except Exception as e:
        state["status_msg"] = f"Connection/Token Error: {e}"
        state["running"] = False

# ==============================================================================
# UI HEADER & STATUS BAR
# ==============================================================================
st.title("📈 Nifty Option Signal PRO v28 - Control App")

col_s1, col_s2, col_s3 = st.columns(3)
col_s1.metric("Algo Status", "🟢 ON" if state["running"] else "🔴 OFF")
col_s2.metric("Order Mode", "⚡ AUTO LIVE ORDER" if algo.CONFIG["AUTO_PLACE_ORDER"] else "🔔 SIRF ALERTS")
col_s3.metric("Last Heartbeat", state["last_update"])
st.info(f"**Current Status:** {state['status_msg']}")

# ==============================================================================
# TABS: 1. Daily Control | 2. Strategy Settings | 3. Backtest | 4. Trade Report
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 1. Daily Login & ON/OFF",
    "⚙️ 2. All Settings",
    "📊 3. Backtest",
    "📋 4. Real Trade Report"
])

# ------------------------------------------------------------------------------
# TAB 1: DAILY DHAN TOKEN & START / STOP / MANUAL EXIT
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🔑 Subah 9:00 Baje Dhan Token Dalein")
    c1, c2 = st.columns(2)
    with c1:
        client_id = st.text_input("Dhan Client ID", value=algo.CONFIG.get("DHAN_CLIENT_ID", ""))
    with c2:
        access_token = st.text_input("Today's Dhan Access Token", value=algo.CONFIG.get("DHAN_ACCESS_TOKEN", ""), type="password")

    auto_order = st.toggle("⚡ Auto Live Order Place Karein (Blue Arrow par Broker me real order jayega)", value=algo.CONFIG["AUTO_PLACE_ORDER"])

    if st.button("💾 Save Token & Order Mode", use_container_width=True):
        algo.CONFIG["DHAN_CLIENT_ID"] = client_id.strip()
        algo.CONFIG["DHAN_ACCESS_TOKEN"] = access_token.strip()
        algo.CONFIG["AUTO_PLACE_ORDER"] = auto_order
        st.success("✅ Token aur Order Mode save ho gaya!")

    st.divider()
    st.subheader("🎛️ Algo Master Control (Start / Stop / Exit)")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶️ START ALGO (ON)", type="primary", use_container_width=True, disabled=state["running"]):
            if not access_token or access_token == "YOUR_DHAN_ACCESS_TOKEN":
                st.error("❌ Pehle upar aaj ka Dhan Access Token dalein aur Save karein!")
            else:
                algo.CONFIG["DHAN_CLIENT_ID"] = client_id.strip()
                algo.CONFIG["DHAN_ACCESS_TOKEN"] = access_token.strip()
                algo.CONFIG["AUTO_PLACE_ORDER"] = auto_order
                algo.CONFIG["RUN_MODE"] = "LIVE"
                state["running"] = True
                t = threading.Thread(target=live_algo_loop, daemon=True)
                state["thread"] = t
                t.start()
                st.rerun()

    with b2:
        if st.button("⏹️ STOP ALGO (OFF)", use_container_width=True, disabled=not state["running"]):
            state["running"] = False
            state["status_msg"] = "Stopped manually by user."
            st.rerun()

    with b3:
        if st.button("🚨 MANUAL EXIT NOW", use_container_width=True):
            eng = state.get("engine")
            conn = state.get("connector")
            if eng and conn and eng.posSt != 0:
                df_now = conn.get_candles(algo.CONFIG["CHART_SYMBOL"], interval="5", days=1)
                if not df_now.empty:
                    eng.manual_exit_now(df_now["close"].iloc[-1], dt.datetime.now(algo.IST), reason="WEB_MANUAL_EXIT")
                    st.warning("⚠️ Active Position Manual Exit kar di gayi hai!")
            else:
                st.info("Abhi koi active open position nahi hai.")

    # Live Active Position & Logs Display
    eng = state.get("engine")
    if eng:
        st.divider()
        st.subheader("📡 Live Algo Status")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Real Trades", eng.real_trade_count)
        m2.metric("Broker Orders Sent", eng.real_live_orders_sent)
        m3.metric("Session Wins / Loss", f"{eng.winN} / {eng.lossN}")
        m4.metric("Session Net Pts", f"{eng.totPnl:+.1f} pts")

        if eng.posSt != 0:
            side_txt = "CE (Call)" if eng.posSt == 1 else "PE (Put)"
            st.warning(f"🔥 **ACTIVE TRADE:** {int(eng.activeStrike)} {side_txt} [{eng.activeExpiry}] | Entry: {eng.posEn:.1f} | SL: {eng.posSl:.1f} | T1: {eng.posT1:.1f} | T2: {eng.posT2:.1f}")
        if eng.logs:
            st.write("**Recent Trade Logs:**")
            for lg in eng.logs:
                st.code(lg)

# ------------------------------------------------------------------------------
# TAB 2: ALL STRATEGY & OPTION SETTINGS (BAHAR SE CONTROL)
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("🎯 Option, Strike, Expiry & Exit Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        strike_mode = st.selectbox("Strike Mode", ["ATM", "ITM_1", "ITM_2", "OTM_1"], index=["ATM", "ITM_1", "ITM_2", "OTM_1"].index(algo.PARAMS["strikeMode"]))
        expiry_mode = st.selectbox("Expiry Mode", ["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"], index=["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY", "MANUAL"].index(algo.PARAMS["expiryMode"]))
        manual_exp = st.text_input("Manual Expiry (YYYY-MM-DD)", value=algo.PARAMS["manualExpiry"])
    with col2:
        exit_mode = st.selectbox("Target Exit Mode", ["T1", "T2", "T1_T2", "MANUAL"], index=["T1", "T2", "T1_T2", "MANUAL"].index(algo.PARAMS["exitMode"]))
        t1_pct = st.number_input("T1_T2 Mode me T1 Exit %", min_value=10, max_value=90, value=int(algo.PARAMS["t1ExitPct"]))
        capital = st.number_input("Capital (Rs)", min_value=10000.0, value=float(algo.PARAMS["capital"]), step=10000.0)
    with col3:
        risk_pct = st.number_input("Risk Per Trade (%)", min_value=0.1, max_value=10.0, value=float(algo.PARAMS["riskPct"]), step=0.1)
        sl_mult = st.number_input("SL ATR Multiplier", min_value=0.5, max_value=5.0, value=float(algo.PARAMS["slMult"]), step=0.1)
        rr_t = st.number_input("Target 1 Risk:Reward", min_value=1.0, max_value=5.0, value=float(algo.PARAMS["rrT"]), step=0.5)

    st.divider()
    st.subheader("🛡️ Filters & Signal Toggles (ON / OFF)")
    f1, f2, f3 = st.columns(3)
    with f1:
        allow_ce = st.checkbox("Allow CE (Call Buy)", value=algo.PARAMS["allowCE"])
        allow_pe = st.checkbox("Allow PE (Put Buy)", value=algo.PARAMS["allowPE"])
        wf_on = st.checkbox("2-Step Blue Arrow Confirmation (wfOn)", value=algo.PARAMS["wfOn"])
        mtf_on = st.checkbox("Multi-Timeframe Agree (mtfOn)", value=algo.PARAMS["mtfOn"])
    with f2:
        adx_on = st.checkbox("Sideways ADX Filter (adxOn)", value=algo.PARAMS["adxOn"])
        adx_min = st.number_input("Min ADX Threshold", min_value=10.0, max_value=40.0, value=float(algo.PARAMS["adxMin"]))
        di_on = st.checkbox("DI Directional Filter (diOn)", value=algo.PARAMS["diOn"])
        dg_on = st.checkbox("Daily 20MA Direction Gate (dgOn)", value=algo.PARAMS["dgOn"])
    with f3:
        auto_oc = st.checkbox("Option Chain OI Filter (autoOc)", value=algo.PARAMS["autoOc"])
        ov_on = st.checkbox("Option Volume PCR (ovOn)", value=algo.PARAMS["ovOn"])
        oi_prob_on = st.checkbox("OI+Vol Probability Filter", value=algo.PARAMS["oiProbFilterOn"])
        high_prob_only = st.checkbox("Sirf HIGH PROB Signals Par Trade", value=algo.PARAMS["requireHighProbOnly"])

    if st.button("✅ Apply & Save All Settings", type="primary", use_container_width=True):
        algo.PARAMS["strikeMode"] = strike_mode
        algo.PARAMS["expiryMode"] = expiry_mode
        algo.PARAMS["manualExpiry"] = manual_exp
        algo.PARAMS["exitMode"] = exit_mode
        algo.PARAMS["t1ExitPct"] = t1_pct
        algo.PARAMS["capital"] = capital
        algo.PARAMS["riskPct"] = risk_pct
        algo.PARAMS["slMult"] = sl_mult
        algo.PARAMS["rrT"] = rr_t
        algo.PARAMS["allowCE"] = allow_ce
        algo.PARAMS["allowPE"] = allow_pe
        algo.PARAMS["wfOn"] = wf_on
        algo.PARAMS["mtfOn"] = mtf_on
        algo.PARAMS["adxOn"] = adx_on
        algo.PARAMS["adxMin"] = adx_min
        algo.PARAMS["diOn"] = di_on
        algo.PARAMS["dgOn"] = dg_on
        algo.PARAMS["autoOc"] = auto_oc
        algo.PARAMS["ovOn"] = ov_on
        algo.PARAMS["oiProbFilterOn"] = oi_prob_on
        algo.PARAMS["requireHighProbOnly"] = high_prob_only
        st.success("🎉 Saari settings turant update ho gayi hain!")

# ------------------------------------------------------------------------------
# TAB 3: HISTORICAL BACKTEST (1-CLICK RUN)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📊 Historical Data Par Backtest Chalayein")
    bc1, bc2 = st.columns(2)
    with bc1:
        bt_days = st.number_input("Kitne Din Ka Backtest Chahiye?", min_value=5, max_value=90, value=int(algo.CONFIG["BACKTEST_DAYS"]))
    with bc2:
        bt_mode = st.selectbox("Backtest Entry Type", ["BOTH", "REAL_BLUE_ONLY", "ALL_SIGNALS"])

    if st.button("🚀 Run Backtest Now", type="primary", use_container_width=True):
        if not algo.CONFIG.get("DHAN_ACCESS_TOKEN") or algo.CONFIG["DHAN_ACCESS_TOKEN"] == "YOUR_DHAN_ACCESS_TOKEN":
            st.error("❌ Backtest ke liye Dhan historical data chahiye — pehle Tab 1 me Dhan Token save karein.")
        else:
            with st.spinner(f"Pichhle {bt_days} din ka data fetch karke Backtest chalaya ja raha hai..."):
                try:
                    algo.CONFIG["BACKTEST_DAYS"] = int(bt_days)
                    algo.CONFIG["BACKTEST_ENTRY_TYPE"] = bt_mode
                    conn = algo.BrokerConnector(algo.CONFIG)
                    algo.run_backtest(conn, days=int(bt_days))
                    st.success("✅ Backtest Complete! Neeche generated CSV report dekhein:")

                    for m_lbl in (["ALL_SIGNALS", "REAL_BLUE_ONLY"] if bt_mode == "BOTH" else [bt_mode]):
                        csv_f = f"backtest_{m_lbl}_{algo.PARAMS['strikeMode']}_{algo.PARAMS['exitMode']}.csv"
                        if os.path.exists(csv_f):
                            df_bt = pd.read_csv(csv_f)
                            st.write(f"### {m_lbl} ({len(df_bt)} Trades | Net Points: {df_bt['PnL_Pts'].sum():+.2f})")
                            st.dataframe(df_bt, use_container_width=True)
                except Exception as e:
                    st.error(f"Backtest Error: {e}")

# ------------------------------------------------------------------------------
# TAB 4: REAL LIVE TRADE JOURNAL REPORT
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("📋 Algo Real Live Trades Hisab")
    if st.button("🔄 Refresh Report"):
        st.rerun()

    csv_file = algo.CONFIG.get("REAL_TRADES_CSV", "live_real_trades_journal.csv")
    if os.path.exists(csv_file):
        df_real = pd.read_csv(csv_file)
        st.dataframe(df_real, use_container_width=True)
    else:
        st.info("Abhi tak koi real live trade record nahi hua hai.")
