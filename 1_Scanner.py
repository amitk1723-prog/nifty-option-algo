# pages/1_Scanner.py
# Sector strength + OI Spurts + Pullback signals. Main app ka connected Dhan session use karta hai.
import time
import datetime as dt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sector + OI + Signal Scanner", layout="wide")
IST = "Asia/Kolkata"

# Sector -> F&O stocks (edit kar sakte ho; master me na mile to skip ho jata hai)
SECTORS = {
    "AUTO": ["MARUTI", "M&M", "TMPV", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "TVSMOTOR", "ASHOKLEY", "BOSCHLTD", "BHARATFORG"],
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS"],
    "BANK": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANKBARODA", "PNB", "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "CANBK"],
    "FIN SERVICES": ["BAJFINANCE", "BAJAJFINSV", "SBILIFE", "HDFCLIFE", "CHOLAFIN", "SHRIRAMFIN", "MUTHOOTFIN", "JIOFIN"],
    "PHARMA": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "ALKEM"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "GODREJCP", "COLPAL", "MARICO", "TATACONSUM", "VBL"],
    "METAL": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "JINDALSTEL", "SAIL", "NMDC", "NATIONALUM", "HINDZINC", "APLAPOLLO"],
    "ENERGY": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL", "COALINDIA", "NTPC", "POWERGRID", "TATAPOWER"],
    "REALTY": ["DLF", "GODREJPROP", "OBEROIRLTY", "LODHA", "PRESTIGE", "PHOENIXLTD"],
    "CAP GOODS": ["LT", "SIEMENS", "ABB", "BHEL", "HAL", "BEL", "CUMMINSIND"],
}


# ---------------- helpers ----------------
def build_universe(conn):
    """Main app ki already-loaded scrip master se F&O stocks ke IDs nikalta hai."""
    df = conn.inst["_DF"]
    nse = df[df["SEM_EXM_EXCH_ID"] == "NSE"]
    eq = nse[nse["SEM_INSTRUMENT_NAME"] == "EQUITY"].drop_duplicates("SEM_TRADING_SYMBOL")
    eq = dict(zip(eq["SEM_TRADING_SYMBOL"], eq["SEM_SMST_SECURITY_ID"].astype(int)))
    fut = nse[nse["SEM_INSTRUMENT_NAME"] == "FUTSTK"].copy()
    fut["exp"] = pd.to_datetime(fut["SEM_EXPIRY_DATE"], errors="coerce")
    fut = fut[fut["exp"].dt.date >= dt.date.today()]
    fut["und"] = fut["SEM_TRADING_SYMBOL"].str.rsplit("-", n=2).str[0]
    fut = fut.sort_values("exp").drop_duplicates("und")
    fut = dict(zip(fut["und"], fut["SEM_SMST_SECURITY_ID"].astype(int)))
    return eq, fut


def get_quotes(dhan, eq_ids, fut_ids):
    r = dhan.quote_data({"NSE_EQ": list(eq_ids), "NSE_FNO": list(fut_ids)})
    if not isinstance(r, dict) or r.get("status") != "success":
        raise RuntimeError(f"quote_data fail: {str(r)[:300]}")
    d = r.get("data", {})
    return d["data"] if "data" in d else d


def get_candles_5m(dhan, secid, days=6):
    """Main app jaisa hi Dhan intraday call (keyword style) + same timestamp fix."""
    to = dt.datetime.now()
    fr = to - dt.timedelta(days=days)
    res = dhan.intraday_minute_data(
        security_id=str(secid), exchange_segment="NSE_EQ", instrument_type="EQUITY",
        from_date=fr.strftime("%Y-%m-%d 09:15:00"), to_date=to.strftime("%Y-%m-%d 15:30:00"), interval=5)
    d = res.get("data", {}) if isinstance(res, dict) else {}
    if not isinstance(d, dict) or not d.get("timestamp"):
        return None
    ts = pd.Series(d["timestamp"], dtype="float64")
    if ts.max() < time.time() - 3 * 365 * 86400:
        ts = ts + 315532800
    n = len(d["close"])
    df = pd.DataFrame({"open": d["open"], "high": d["high"], "low": d["low"], "close": d["close"],
                       "volume": d.get("volume", [0] * n)})
    df.index = pd.to_datetime(ts.values, unit="s", utc=True).tz_convert(IST)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if len(df) and df.index[-1] + pd.Timedelta(minutes=5) > pd.Timestamp.now(tz=IST):
        df = df.iloc[:-1]  # forming candle hata do
    return df


def check_signal(df, side, lookback, vol_ratio):
    """Vande Bharat style: trend ke saath low-volume pullback, phir pullback high/low ka breakout + VWAP side."""
    if df is None or df.empty:
        return None
    day = df.index[-1].date()
    t = df[df.index.date == day]
    prev = df[df.index.date < day]
    if len(t) < lookback + 3 or prev.empty:
        return None
    pday = prev[prev.index.date == prev.index.date[-1]]
    pdh, pdl = pday["high"].max(), pday["low"].min()
    tp = (t["high"] + t["low"] + t["close"]) / 3
    vwap = (tp * t["volume"]).cumsum() / t["volume"].cumsum()
    avgv = t["volume"].mean()
    last = t.iloc[-1]
    w = t.iloc[-(lookback + 1):-1]
    wv = w["volume"].mean() / avgv if avgv else 1
    if side == "BUY":
        ok = ((w["close"] < w["open"]).sum() >= 2 and wv < vol_ratio
              and last["close"] > w["high"].max() and last["close"] > vwap.iloc[-1])
        sl = w["low"].min()
        tgt = last["close"] + 2 * (last["close"] - sl)
        lvl = f"PDH {pdh:.2f} " + ("(upar)" if last["close"] > pdh else "(neeche)")
    else:
        ok = ((w["close"] > w["open"]).sum() >= 2 and wv < vol_ratio
              and last["close"] < w["low"].min() and last["close"] < vwap.iloc[-1])
        sl = w["high"].max()
        tgt = last["close"] - 2 * (sl - last["close"])
        lvl = f"PDL {pdl:.2f} " + ("(neeche)" if last["close"] < pdl else "(upar)")
    if not ok:
        return None
    return {"Signal": side, "Close": round(last["close"], 2), "SL": round(sl, 2), "Target 1:2": round(tgt, 2),
            "PullbackVol/Avg": round(wv, 2), "VWAP": round(vwap.iloc[-1], 2), "Level": lvl,
            "Candle": last.name.strftime("%H:%M")}


@st.cache_resource
def oi_store():
    return {"snaps": []}  # sab sessions me shared OI snapshots


def oi_class(pchg, oichg):
    if oichg > 0:
        return "Long Buildup" if pchg > 0 else "Short Buildup"
    return "Short Covering" if pchg > 0 else "Long Unwinding"


# ---------------- UI ----------------
st.title("Sector + OI Spurts + Pullback Signal Scanner")

conn = st.session_state.get("broker_conn")
if conn is None:
    st.warning("Pehle main page (NIFTY OPTION SIGNAL PRO) kholo, wahan Dhan Client ID aur Access Token daalo "
               "(Broker Connected dikhe), phir yahan wapas aao.")
    st.stop()
if getattr(conn, "broker", "") != "DHAN":
    st.warning("Ye scanner abhi sirf Dhan ke liye hai. Main page pe Broker = DHAN chuno.")
    st.stop()
dhan = conn.dhan

with st.sidebar:
    st.header("Scanner Settings")
    topk = st.slider("Top/Bottom sectors", 1, 4, 2)
    max_n = st.slider("Max stocks per side (signal check)", 3, 15, 8)
    lookback = st.slider("Pullback candles (5m)", 2, 6, 3)
    vol_ratio = st.slider("Pullback volume < avg x", 0.3, 1.2, 0.8, 0.05)
    oi_min = st.slider("OI lookback (min)", 5, 60, 15)
    oi_thr = st.slider("Min OI change %", 0.5, 10.0, 2.0, 0.5)
    auto = st.checkbox("Auto refresh", value=False)
    gap = st.number_input("Refresh seconds", 60, 600, 120, 30)
    go = st.button("Scan now", use_container_width=True, type="primary")

if not (go or auto):
    st.caption("Sidebar me Scan now dabao.")
    st.stop()

try:
    if "scan_universe" not in st.session_state:
        st.session_state["scan_universe"] = build_universe(conn)
    eq, fut = st.session_state["scan_universe"]

    rows = [{"Sector": sec, "Symbol": s, "eq": eq[s], "fut": fut.get(s)}
            for sec, syms in SECTORS.items() for s in syms if s in eq]
    u = pd.DataFrame(rows)
    q = get_quotes(dhan, u["eq"].tolist(), u["fut"].dropna().astype(int).tolist())
    qe, qf = q.get("NSE_EQ", {}), q.get("NSE_FNO", {})

    def pct(x):
        pc = (x.get("ohlc") or {}).get("close") or 0
        return (x.get("last_price", 0) - pc) / pc * 100 if pc else 0.0

    u["LTP"] = u["eq"].map(lambda i: qe.get(str(i), {}).get("last_price"))
    u["%Chg"] = u["eq"].map(lambda i: pct(qe.get(str(i), {})))
    u["Volume"] = u["eq"].map(lambda i: qe.get(str(i), {}).get("volume"))
    u["OI"] = u["fut"].map(lambda i: qf.get(str(int(i)), {}).get("oi") if pd.notna(i) else None)
    u = u.dropna(subset=["LTP"])

    sec = (u.groupby("Sector").agg(Avg_Chg=("%Chg", "mean"), Breadth=("%Chg", lambda s: (s > 0).mean() * 100),
                                   Stocks=("Symbol", "count")).sort_values("Avg_Chg", ascending=False).round(2))
    top, bot = list(sec.index[:topk]), list(sec.index[-topk:])

    # OI snapshots
    store = oi_store()
    now = dt.datetime.now()
    if not store["snaps"] or (now - store["snaps"][-1][0]).total_seconds() >= 60:
        store["snaps"].append((now, {r.Symbol: (r.OI, r.LTP) for r in u.itertuples() if pd.notna(r.OI)}))
    store["snaps"] = [x for x in store["snaps"] if (now - x[0]).total_seconds() < 4 * 3600]
    old = [x for x in store["snaps"] if (now - x[0]).total_seconds() >= oi_min * 60]
    base = old[-1] if old else (store["snaps"][0] if len(store["snaps"]) > 1 else None)

    oi_rows = []
    if base:
        for r in u.itertuples():
            if r.Symbol in base[1] and pd.notna(r.OI) and base[1][r.Symbol][0]:
                o0, p0 = base[1][r.Symbol]
                oc, pc_ = (r.OI - o0) / o0 * 100, (r.LTP - p0) / p0 * 100
                if abs(oc) >= oi_thr:
                    oi_rows.append({"Symbol": r.Symbol, "Sector": r.Sector, "OI %": round(oc, 2),
                                    "Price % (same window)": round(pc_, 2), "Type": oi_class(pc_, oc)})
    oi_df = pd.DataFrame(oi_rows).sort_values("OI %", key=abs, ascending=False) if oi_rows else pd.DataFrame()

    # signals
    cands = []
    for side, secs in (("BUY", top), ("SELL", bot)):
        d = u[u["Sector"].isin(secs)]
        d = d[d["%Chg"] > 0] if side == "BUY" else d[d["%Chg"] < 0]
        for r in d.reindex(d["%Chg"].abs().sort_values(ascending=False).index).head(max_n).itertuples():
            cands.append((side, r))
    sigs, prog = [], st.progress(0.0, text="Signals check ho rahe hain...")
    for i, (side, r) in enumerate(cands):
        try:
            s = check_signal(get_candles_5m(dhan, r.eq), side, lookback, vol_ratio)
        except Exception:
            s = None
        if s:
            oi_t = ""
            if not oi_df.empty and r.Symbol in set(oi_df["Symbol"]):
                oi_t = oi_df[oi_df["Symbol"] == r.Symbol].iloc[0]["Type"]
            sigs.append({"Symbol": r.Symbol, "Sector": r.Sector, **s, "OI": oi_t})
        prog.progress((i + 1) / max(len(cands), 1))
        time.sleep(0.3)  # Dhan data API rate limit
    prog.empty()

    st.caption(f"Last scan: {now.strftime('%H:%M:%S')} | Top: {', '.join(top)} | Bottom: {', '.join(bot)}")
    t1, t2, t3, t4 = st.tabs(["Signals", "Sectors", "OI Spurts", "Stocks"])
    with t1:
        if sigs:
            st.dataframe(pd.DataFrame(sigs), use_container_width=True)
        else:
            st.info("Abhi koi signal nahi.")
    with t2:
        st.dataframe(sec, use_container_width=True)
    with t3:
        if base is None:
            st.info("Pehla snapshot save hua. Kuch minute baad dobara scan karo.")
        elif oi_df.empty:
            st.info(f"Pichle ~{int((now - base[0]).total_seconds() / 60)} min me {oi_thr}% se zyada OI change nahi.")
        else:
            st.dataframe(oi_df, use_container_width=True)
    with t4:
        st.dataframe(u[["Sector", "Symbol", "LTP", "%Chg", "Volume", "OI"]].sort_values("%Chg", ascending=False),
                     use_container_width=True)
except Exception as e:
    st.error(f"Scanner error: {e}")

if auto:
    time.sleep(int(gap))
    st.rerun()
