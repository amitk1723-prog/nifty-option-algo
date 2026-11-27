# pages/1_Scanner.py
# Sector strength + OI Spurts + Pullback signals. Main app ka connected Dhan session use karta hai.
# v4: sector ke saamne Scanner avg % + asli NSE Index % (dono), Divergence badge, robust index matching,
#     28 unmapped stocks ka sector map
import re
import time
import json
import datetime as dt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sector + OI + Signal Scanner", layout="wide")
IST = "Asia/Kolkata"
SIG_FILE = "signal_log.json"  # best-effort save (app restart par bhi list bachne ki koshish)
EXPECTED_FNO = 218  # F&O stocks ki expected ginti

# Sector -> F&O stocks (edit kar sakte ho). Jo stock yahan nahi hoga wo "OTHERS" me dikhega.
SECTORS = {
    "AUTO": ["MARUTI", "M&M", "TMPV", "TMCV", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "TVSMOTOR", "ASHOKLEY",
             "BOSCHLTD", "BHARATFORG", "MOTHERSON", "SONACOMS", "UNOMINDA", "EXIDEIND", "TIINDIA", "MRF",
             "ATHERENERG", "FORCEMOT", "HYUNDAI"],
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS",
           "KPITTECH", "TATAELXSI", "TATATECH", "CYIENT", "LTM", "SAGILITY"],
    "BANK": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANKBARODA", "PNB",
             "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "CANBK", "BANDHANBNK", "RBLBANK", "YESBANK", "UNIONBANK",
             "INDIANB", "BANKINDIA", "CUB", "KARURVYSYA", "MAHABANK", "UJJIVANSFB"],
    "FIN SERVICES": ["BAJFINANCE", "BAJAJFINSV", "SBILIFE", "HDFCLIFE", "ICICIGI", "ICICIPRULI", "LICI", "SBICARD",
                     "CHOLAFIN", "SHRIRAMFIN", "MUTHOOTFIN", "MANAPPURAM", "JIOFIN", "PFC", "RECLTD", "IRFC",
                     "LICHSGFIN", "POONAWALLA", "HDFCAMC", "CDSL", "BSE", "ANGELONE", "MFSL", "360ONE",
                     "NUVAMA", "PNBHOUSING", "CAMS", "IREDA", "HUDCO", "LTF", "KFINTECH", "SAMMAANCAP",
                     "PAYTM", "POLICYBZR", "ABCAPITAL", "ANANDRATHI", "ICICILIFE", "MCX", "MOTILALOFS",
                     "NAM-INDIA"],
    "PHARMA": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE",
               "ALKEM", "BIOCON", "GLENMARK", "MANKIND", "LAURUSLABS", "GRANULES", "SYNGENE", "PPLPHARMA"],
    "HEALTHCARE": ["APOLLOHOSP", "MAXHEALTH", "FORTIS", "LALPATHLAB"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "GODREJCP", "COLPAL", "MARICO",
             "TATACONSUM", "VBL", "UNITDSPR", "PATANJALI", "GODFRYPHLP", "RADICO"],
    "METAL": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "JINDALSTEL", "SAIL", "NMDC", "NATIONALUM",
              "HINDZINC", "APLAPOLLO", "JSL"],
    "OIL & GAS": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL", "COALINDIA", "HINDPETRO", "OIL", "PETRONET", "IGL"],
    "POWER": ["NTPC", "POWERGRID", "TATAPOWER", "ADANIGREEN", "ADANIENSOL", "NHPC", "JSWENERGY", "TORNTPOWER",
              "SUZLON", "INOXWIND", "WAAREEENER", "NTPCGREEN", "POWERINDIA", "PREMIERENE", "ADANIPOWER"],
    "REALTY": ["DLF", "GODREJPROP", "OBEROIRLTY", "LODHA", "PRESTIGE", "PHOENIXLTD"],
    "CAP GOODS": ["LT", "SIEMENS", "ABB", "BHEL", "HAL", "BEL", "CUMMINSIND", "BDL", "MAZDOCK", "COCHINSHIP",
                  "POLYCAB", "KEI", "HAVELLS", "CGPOWER", "KAYNES", "DIXON", "SOLARINDS", "SUPREMEIND",
                  "ASTRAL", "NBCC", "RVNL", "APARINDS", "DATAPATTNS", "ENRIN", "GVT&D", "SYRMA"],
    "INFRA & LOGISTICS": ["ADANIPORTS", "ADANIENT", "GMRAIRPORT", "IRCTC", "CONCOR", "DELHIVERY", "INDIGO"],
    "CEMENT": ["ULTRACEMCO", "AMBUJACEM", "SHREECEM", "GRASIM", "DALBHARAT"],
    "CONSUMER": ["TITAN", "ASIANPAINT", "BERGEPAINT", "PIDILITIND", "TRENT", "DMART", "JUBLFOOD", "PAGEIND",
                 "KALYANKJIL", "VOLTAS", "BLUESTARCO", "CROMPTON", "INDHOTEL", "NYKAA", "ETERNAL", "SWIGGY",
                 "AMBER", "PGEL", "VMM"],
    "CHEMICALS": ["UPL", "SRF", "PIIND", "TATACHEM", "COROMANDEL", "ACUTAAS", "NAVINFLUOR"],
    "TELECOM & MEDIA": ["BHARTIARTL", "IDEA", "INDUSTOWER", "TATACOMM", "NAUKRI", "PBFINTECH"],
}
SECTOR_OF = {s: sec for sec, syms in SECTORS.items() for s in syms}  # ek symbol = ek sector

# Sector -> asli NSE index (alag-alag naam ke options; jo scrip master me pehle mile wahi use hoga).
# Jin sectors ka koi sahi NSE index nahi (POWER, CAP GOODS, CEMENT, INFRA, TELECOM) unhe jaan-bujhkar khali rakha hai,
# taki galat index ka % na dikhe. Chaho to yahan apna index jod sakte ho.
INDEX_ALIASES = {
    "BANK": ["NIFTY BANK", "BANKNIFTY"],
    "IT": ["NIFTY IT", "NIFTYIT"],
    "AUTO": ["NIFTY AUTO"],
    "PHARMA": ["NIFTY PHARMA"],
    "HEALTHCARE": ["NIFTY HEALTHCARE INDEX", "NIFTY HEALTHCARE"],
    "FMCG": ["NIFTY FMCG"],
    "METAL": ["NIFTY METAL"],
    "REALTY": ["NIFTY REALTY"],
    "FIN SERVICES": ["NIFTY FIN SERVICE", "NIFTY FINANCIAL SERVICES", "FINNIFTY", "NIFTY FINSERVICE"],
    "OIL & GAS": ["NIFTY OIL AND GAS", "NIFTY OIL & GAS"],
    "CHEMICALS": ["NIFTY CHEMICALS", "NIFTY CHEMICALS INDEX"],
    "CONSUMER": ["NIFTY INDIA CONSUMPTION", "NIFTY CONSUMPTION"],  # approx (Titan, Trent, DMart, paints...)
}
DIV_MIN = 0.10  # dono % itne se zyada hon aur sign ulta ho tabhi Divergence badge


# ---------------- helpers ----------------
def market_is_open(now):
    """now = naive IST datetime. NSE: Mon-Fri 9:15 - 15:30."""
    return now.weekday() < 5 and dt.time(9, 15) <= now.time() <= dt.time(15, 30)


def _norm(x):
    """Naam compare karne ke liye: CAPS, & -> AND, baaki sab symbols/space hata do."""
    return re.sub(r"[^A-Z0-9]", "", str(x).upper().replace("&", "AND"))


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


def index_pct(conn, dhan, pct_fn):
    """Sector index ka asli % change (NSE index quote se).
    Return: (pct_by_sector, index_name_by_sector, error_text).
    Naam scrip master ke kai columns me dhoondhta hai (trading symbol / symbol name / custom symbol)."""
    try:
        df = conn.inst["_DF"]
        ix = df[df["SEM_INSTRUMENT_NAME"] == "INDEX"]
        name_cols = [c for c in ("SEM_TRADING_SYMBOL", "SM_SYMBOL_NAME", "SEM_CUSTOM_SYMBOL") if c in ix.columns]
        by_name = {}
        for _, row in ix.iterrows():
            sid = int(row["SEM_SMST_SECURITY_ID"])
            for c in name_cols:
                by_name.setdefault(_norm(row[c]), (sid, str(row[c])))
        ids, names = {}, {}
        for sec_name, aliases in INDEX_ALIASES.items():
            for a in aliases:
                hit = by_name.get(_norm(a))
                if hit:
                    ids[sec_name], names[sec_name] = hit[0], hit[1]
                    break
        if not ids:
            return {}, {}, "scrip master me koi sector index nahi mila"
        r = dhan.quote_data({"IDX_I": list(ids.values())})
        if not isinstance(r, dict) or r.get("status") != "success":
            return {}, names, f"index quote fail: {str(r)[:200]}"
        d = r.get("data", {})
        d = (d["data"] if "data" in d else d).get("IDX_I", {})
        out = {sec_name: pct_fn(d[str(i)]) for sec_name, i in ids.items() if str(i) in d}
        return out, names, ""
    except Exception as e:
        return {}, {}, f"index error: {e}"


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def daily_change_pct(_dhan, secid, day_key):
    """Fallback: daily candles se last close vs pichla close. day_key = aaj ki date (cache roz refresh)."""
    try:
        to = dt.date.today() + dt.timedelta(days=1)
        fr = to - dt.timedelta(days=12)
        res = _dhan.historical_daily_data(
            security_id=str(secid), exchange_segment="NSE_EQ", instrument_type="EQUITY",
            from_date=fr.strftime("%Y-%m-%d"), to_date=to.strftime("%Y-%m-%d"))
        c = (res.get("data") or {}).get("close") if isinstance(res, dict) else None
        if c and len(c) >= 2 and c[-2]:
            return (c[-1] - c[-2]) / c[-2] * 100
    except Exception:
        pass
    return 0.0


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
        df = df.iloc[:-1]  # forming candle hata do (market band me last candle rehti hai)
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
            "Date": last.name.strftime("%d-%b"), "Candle": last.name.strftime("%H:%M")}


@st.cache_resource
def oi_store():
    return {"snaps": []}  # sab sessions me shared OI snapshots


@st.cache_resource
def sig_store():
    """Poore din ka Signal Log (sab sessions me shared). File se bhi load karta hai."""
    log = []
    try:
        with open(SIG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        pass
    return {"log": log if isinstance(log, list) else []}


def add_signals(store, sigs, now):
    """Naye signals log me jodta hai (same Date+Symbol+Side+Candle dobara nahi). Return: naye signals ki ginti."""
    keys = {(x.get("Date"), x.get("Symbol"), x.get("Signal"), x.get("Candle")) for x in store["log"]}
    new = 0
    for s in sigs:
        k = (s["Date"], s["Symbol"], s["Signal"], s["Candle"])
        if k not in keys:
            store["log"].append({"Found At": now.strftime("%d-%b %H:%M:%S"), **s})
            keys.add(k)
            new += 1
    store["log"] = store["log"][-1000:]
    if new:
        try:
            with open(SIG_FILE, "w", encoding="utf-8") as f:
                json.dump(store["log"], f)
        except Exception:
            pass
    return new


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
    gap = st.number_input("Refresh seconds", 60, 600, 120, 30)

# Scan button + Auto refresh main page par (mobile me sidebar kholne ki zarurat nahi)
bc1, bc2 = st.columns([1, 1])
with bc1:
    go = st.button("\U0001f504 Scan now", use_container_width=True, type="primary")
with bc2:
    auto = st.toggle("Auto refresh", value=False, key="scan_auto") if hasattr(st, "toggle") \
        else st.checkbox("Auto refresh", value=False, key="scan_auto")

if not (go or auto):
    st.caption("Upar Scan now dabao. (Settings sidebar me hain)")
    st.stop()

try:
    if "scan_universe" not in st.session_state:
        st.session_state["scan_universe"] = build_universe(conn)
    eq, fut = st.session_state["scan_universe"]

    # Universe = scrip master ke SAARE F&O stocks (sector sirf label hai; na mile to OTHERS)
    rows = [{"Sector": SECTOR_OF.get(s, "OTHERS"), "Symbol": s, "eq": eq[s], "fut": fut[s]}
            for s in sorted(fut) if s in eq]
    miss = sorted(s for s in fut if s not in eq)  # futures hai par equity ID nahi mili
    if len(rows) != EXPECTED_FNO or miss:
        st.warning(f"F&O universe: {len(rows)} stocks (expected {EXPECTED_FNO}). "
                   f"Equity ID nahi mili: {', '.join(miss) or '-'}")
    u = pd.DataFrame(rows)
    q = get_quotes(dhan, u["eq"].tolist(), u["fut"].dropna().astype(int).tolist())
    qe, qf = q.get("NSE_EQ", {}), q.get("NSE_FNO", {})

    now = pd.Timestamp.now(tz=IST).to_pydatetime().replace(tzinfo=None)  # IST time
    mkt_open = market_is_open(now)

    def pct(x):
        """net_change = LTP - pichla close. Live aur market band, dono me sahi (ohlc.close band me aaj ka close ban jata hai)."""
        ltp = x.get("last_price", 0) or 0
        nc = x.get("net_change")
        if nc is not None and ltp:
            pc = ltp - nc
            return nc / pc * 100 if pc else 0.0
        pc = (x.get("ohlc") or {}).get("close") or 0
        return (ltp - pc) / pc * 100 if pc else 0.0

    u["LTP"] = u["eq"].map(lambda i: qe.get(str(i), {}).get("last_price"))
    u["%Chg"] = u["eq"].map(lambda i: pct(qe.get(str(i), {})))
    u["Volume"] = u["eq"].map(lambda i: qe.get(str(i), {}).get("volume"))
    u["OI"] = u["fut"].map(lambda i: qf.get(str(int(i)), {}).get("oi") if pd.notna(i) else None)
    u = u.dropna(subset=["LTP"])

    # Fallback: agar quote se sab 0 aaya (net_change nahi mila) to daily candles se last close vs prev close
    data_src = "quote"
    if len(u) and (u["%Chg"].abs() < 1e-9).all():
        pb = st.progress(0.0, text="Last trading day ka data la rahe hain...")
        vals = []
        for i, sid in enumerate(u["eq"].tolist()):
            vals.append(daily_change_pct(dhan, int(sid), dt.date.today().isoformat()))
            pb.progress((i + 1) / len(u))
            time.sleep(0.15)
        pb.empty()
        u["%Chg"] = vals
        data_src = "daily"

    sec = (u.groupby("Sector").agg(Avg_Chg=("%Chg", "mean"), Breadth=("%Chg", lambda s: (s > 0).mean() * 100),
                                   Stocks=("Symbol", "count")).sort_values("Avg_Chg", ascending=False).round(2))
    # Sector index ka asli % (full free-float market-cap weight) - stocks ke simple average se alag hota hai
    if data_src == "quote":
        ip, ip_names, ip_err = index_pct(conn, dhan, pct)
    else:
        ip, ip_names, ip_err = {}, {}, "quote data nahi aaya (daily fallback), isliye Index % skip"
    sec["Index"] = [ip_names.get(s_, "") for s_ in sec.index]
    sec["Index %"] = [round(ip[s_], 2) if s_ in ip else float("nan") for s_ in sec.index]
    sec["Diff (Avg-Index)"] = (sec["Avg_Chg"] - sec["Index %"]).round(2)

    rank = sec.drop(index="OTHERS", errors="ignore")  # OTHERS ko top/bottom ranking se bahar rakho
    top, bot = list(rank.index[:topk]), list(rank.index[-topk:])

    # OI snapshots (sirf market chalu ho tab save, warna band market ka bekaar snapshot jud jata hai)
    store = oi_store()
    if mkt_open and (not store["snaps"] or (now - store["snaps"][-1][0]).total_seconds() >= 60):
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

    # Naye signals ko Signal Log me jodo (time ke saath)
    slog = sig_store()
    n_new = add_signals(slog, sigs, now)

    status = "\U0001f7e2 LIVE" if mkt_open else "\U0001f4cc Market band - last trading day ka data"
    st.caption(f"{status} | Last scan: {now.strftime('%H:%M:%S')} | Top: {', '.join(top)} | Bottom: {', '.join(bot)}")
    if n_new:
        st.success(f"\U0001f514 {n_new} naya signal mila: " + ", ".join(f"{s['Symbol']} {s['Signal']}" for s in sigs[-n_new:]))

    # Universe info + jin stocks ka sector tay nahi hua
    um = sorted(u.loc[u["Sector"] == "OTHERS", "Symbol"])
    st.caption(f"Total {len(u)} F&O stocks scan hue.")
    if um:
        st.caption(f"Sector nahi mila ({len(um)}): " + ", ".join(um) + " -> inhe SECTORS me jod do.")

    # Index % kis sector ka nahi aaya (taki chupke se gayab na ho)
    no_idx = [s_ for s_ in sec.index if s_ in INDEX_ALIASES and s_ not in ip]
    if ip_err or no_idx:
        st.caption("Index % issue: " + (ip_err + ". " if ip_err else "")
                   + (f"In sectors ka index quote nahi mila: {', '.join(no_idx)}. " if no_idx else "")
                   + "Sectors tab me 'Index' column dekho.")

    # ---------- Market Breadth: Advance / Decline ----------
    total = len(u)
    green = int((u["%Chg"] > 0).sum())
    red = int((u["%Chg"] < 0).sum())
    flat = total - green - red
    gp = (green / total * 100) if total else 0
    rp = (red / total * 100) if total else 0
    st.markdown(
        f"""
<div style="display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 4px 0;">
  <div style="flex:1;min-width:55px;background:#f3f4f6;border-radius:10px;padding:8px 4px;text-align:center;">
    <div style="font-size:13px;color:#555;">A/D Ratio</div><div style="font-size:24px;font-weight:700;color:#111;">{(green / red if red else float(green)):.2f}</div><div style="font-size:12px;color:#555;">Total {total}</div></div>
  <div style="flex:1;min-width:55px;background:#dcfce7;border-radius:10px;padding:8px 4px;text-align:center;">
    <div style="font-size:13px;color:#166534;">\u25b2 Advance</div><div style="font-size:24px;font-weight:700;color:#15803d;">{green}</div>
    <div style="font-size:12px;color:#166534;">{gp:.0f}%</div></div>
  <div style="flex:1;min-width:55px;background:#fee2e2;border-radius:10px;padding:8px 4px;text-align:center;">
    <div style="font-size:13px;color:#991b1b;">\u25bc Decline</div><div style="font-size:24px;font-weight:700;color:#b91c1c;">{red}</div>
    <div style="font-size:12px;color:#991b1b;">{rp:.0f}%</div></div>
  <div style="flex:1;min-width:55px;background:#f3f4f6;border-radius:10px;padding:8px 4px;text-align:center;">
    <div style="font-size:13px;color:#555;">Unchanged</div><div style="font-size:24px;font-weight:700;color:#444;">{flat}</div></div>
</div>
<div style="display:flex;height:12px;border-radius:6px;overflow:hidden;margin-bottom:14px;background:#e5e7eb;">
  <div style="width:{gp:.1f}%;background:#16a34a;"></div><div style="width:{rp:.1f}%;margin-left:auto;background:#dc2626;"></div>
</div>
""".replace("\n  ", "\n").replace("\n    ", "\n"),
        unsafe_allow_html=True,
    )

    # ---------- Sector-wise Green/Red COUNT bar (ek sector = ek line) ----------
    try:
        rows_html = []
        for s_name in sec.index:  # strongest sector sabse upar
            d_s = u[u["Sector"] == s_name]
            g_n = int((d_s["%Chg"] > 0).sum())
            r_n = int((d_s["%Chg"] < 0).sum())
            f_n = len(d_s) - g_n - r_n
            tot_n = max(len(d_s), 1)
            avg = sec.loc[s_name, "Avg_Chg"]
            idx_v = sec.loc[s_name, "Index %"]
            avg_col = "#15803d" if avg > 0 else ("#b91c1c" if avg < 0 else "#555")
            if pd.isna(idx_v):
                idx_txt, div_txt = "", ""
            else:
                idx_col = "#15803d" if idx_v > 0 else ("#b91c1c" if idx_v < 0 else "#555")
                idx_txt = (f' <span style="color:#666;font-size:12px;">| Index</span> '
                           f'<span style="color:{idx_col};font-weight:600;">{idx_v:+.2f}%</span>')
                is_div = avg * idx_v < 0 and abs(avg) >= DIV_MIN and abs(idx_v) >= DIV_MIN
                div_txt = (' <span style="background:#fef3c7;color:#92400e;font-size:11px;font-weight:700;'
                           'padding:1px 6px;border-radius:8px;">\u26a0 Divergence</span>') if is_div else ""
            g_bar = f'<div style="width:{g_n / tot_n * 100:.1f}%;background:#16a34a;color:#fff;font-size:12px;font-weight:700;text-align:center;line-height:22px;">{g_n if g_n else ""}</div>'
            f_bar = f'<div style="width:{f_n / tot_n * 100:.1f}%;background:#9ca3af;"></div>'
            r_bar = f'<div style="width:{r_n / tot_n * 100:.1f}%;background:#dc2626;color:#fff;font-size:12px;font-weight:700;text-align:center;line-height:22px;">{r_n if r_n else ""}</div>'
            rows_html.append(f"""
<div style="margin:0 0 10px 0;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:14px;margin-bottom:3px;">
    <span><b>{s_name}</b> <span style="color:#666;font-size:12px;">Scanner</span> <span style="color:{avg_col};font-weight:600;">{avg:+.2f}%</span>{idx_txt}{div_txt}</span>
    <span style="font-size:13px;"><span style="color:#15803d;font-weight:700;">Adv {g_n}</span> &nbsp; <span style="color:#b91c1c;font-weight:700;">Dec {r_n}</span> &nbsp; <span style="color:#888;">/ {len(d_s)}</span></span>
  </div>
  <div style="display:flex;height:22px;border-radius:6px;overflow:hidden;background:#e5e7eb;">{g_bar}{f_bar}{r_bar}</div>
</div>""")
        st.markdown("#### Sector-wise Advance / Decline")
        st.caption("Scanner = tumhare F&O stocks ka simple average | Index = asli NSE sector index (full weightage)")
        st.markdown("".join(ln.strip() for ln in "".join(rows_html).splitlines()), unsafe_allow_html=True)
    except Exception as ce:
        st.caption(f"Sector chart error: {ce}")

    t1, t2, t3, t4 = st.tabs(["Signals", "Sectors", "OI Spurts", "Stocks"])
    with t1:
        log = slog["log"]
        if not log:
            st.info("Abhi tak koi signal nahi mila. Jaise hi milega, time ke saath yahan list me judta jayega.")
        else:
            c1, c2 = st.columns([2, 1])
            with c1:
                view = st.radio("Dikhao", ["Sab", "Sirf aaj ke", "Sirf BUY", "Sirf SELL"],
                                horizontal=True, key="sig_view", label_visibility="collapsed")
            with c2:
                if st.button("Log clear karo", key="sig_clear"):
                    slog["log"].clear()
                    try:
                        with open(SIG_FILE, "w", encoding="utf-8") as f:
                            json.dump([], f)
                    except Exception:
                        pass
                    st.rerun()
            ldf = pd.DataFrame(log)
            if view == "Sirf aaj ke":
                ldf = ldf[ldf["Date"] == now.strftime("%d-%b")]
            elif view == "Sirf BUY":
                ldf = ldf[ldf["Signal"] == "BUY"]
            elif view == "Sirf SELL":
                ldf = ldf[ldf["Signal"] == "SELL"]
            cols = [c for c in ["Found At", "Date", "Candle", "Symbol", "Sector", "Signal", "Close", "SL",
                                "Target 1:2", "PullbackVol/Avg", "VWAP", "Level", "OI"] if c in ldf.columns]
            ldf = ldf[cols].iloc[::-1]  # naya signal sabse upar
            st.caption(f"Total {len(ldf)} signals (naya upar). 'Found At' = scanner ne kab pakda, 'Candle' = 5m candle ka time.")
            st.dataframe(ldf, use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(sec, use_container_width=True)
    with t3:
        if base is None:
            st.info("Pehla snapshot save hua. Kuch minute baad dobara scan karo." if mkt_open
                    else "Market band hai. OI Spurts sirf market chalu hone par bante hain.")
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
    # 1-1 second ka countdown: is beech koi button/toggle dabao to turant response milega
    cd = st.empty()
    for left in range(int(gap), 0, -1):
        cd.caption(f"Agla auto scan {left} sec me... (band karne ke liye Auto refresh OFF karein)")
        time.sleep(1)
    cd.empty()
    st.rerun()
