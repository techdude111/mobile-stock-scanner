
import os
import time
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="📈 Mobile Stock Scanner", layout="wide")

# --- Mobile-first CSS tweaks
st.markdown("""
<style>
.block-container {padding-top: 0.6rem; padding-bottom: 2rem; padding-left: 0.8rem; padding-right: 0.8rem;}
[data-testid="stSidebar"] {width: 20rem;}
[data-baseweb="table"] div {font-size: 0.9rem;}
thead tr th div {white-space: normal !important;}
</style>
""", unsafe_allow_html=True)

st.title("📈 Mobile Momentum/Gap Scanner")

with st.sidebar:
    with st.expander("Controls", expanded=True):
        tickers_source = st.radio("Ticker input", ["Manual list", "Upload .txt / .csv"], horizontal=False)
        default_list = "AAPL,TSLA,NVDA,AMD,MSFT,AMZN,META,GOOGL,PLTR,SMCI,SOFI,RIOT,MARA,SPY,QQQ,TLRY,NIO"
        if tickers_source == "Manual list":
            tickers_text = st.text_area("Tickers", default_list, height=70, help="Comma or space separated")
            raw_tickers = tickers_text.replace("\n"," ").replace(";", " ").replace("|"," ").split()
        else:
            up = st.file_uploader("Upload tickers", type=["txt","csv"])
            raw_tickers = []
            if up is not None:
                if up.name.endswith(".csv"):
                    import io
                    raw = up.read().decode("utf-8", errors="ignore")
                    try:
                        dfup = pd.read_csv(io.StringIO(raw))
                        raw_tickers = dfup.iloc[:,0].astype(str).tolist()
                    except Exception:
                        raw_tickers = [x.strip() for x in raw.split(",") if x.strip()]
                else:
                    raw = up.read().decode("utf-8", errors="ignore")
                    raw_tickers = [x.strip() for x in raw.replace("\n"," ").replace(",", " ").split(" ") if x.strip()]

        raw_tickers = [t.upper().strip() for t in raw_tickers if t.strip()]
        raw_tickers = list(dict.fromkeys(raw_tickers))

        min_price, max_price = st.slider("Price $", 0.0, 500.0, (0.5, 100.0))
        min_gap = st.slider("Min Gap %", -50.0, 100.0, 2.0)
        min_rel_vol = st.slider("Min Rel Vol (30d)", 0.0, 20.0, 1.5)
        show_intraday = st.toggle("Show 5-min stats", True)
        refresh = st.number_input("Auto-refresh sec (0=off)", 0, 900, 0, 5)

st.caption("Tip: Use your phone’s Share → Add to Home Screen to pin this like an app.")

@st.cache_data(ttl=60, show_spinner=False)
def get_daily_snapshot(tickers):
    import yfinance as yf
    data = []
    tickers = [t for t in tickers if t]
    if not tickers:
        return pd.DataFrame()
    yfs = yf.Tickers(" ".join(tickers))
    for t, y in yfs.tickers.items():
        try:
            info = y.fast_info
            price = info.last_price
            prev_close = info.previous_close
            volume = info.last_volume
            day_high = info.day_high
            day_low = info.day_low
            currency = info.currency
            hist = y.history(period="60d", interval="1d", actions=False)
            avg_vol_30d = float(hist["Volume"].tail(30).mean()) if not hist.empty else np.nan
            gap_pct = ((price - prev_close) / prev_close * 100.0) if prev_close else np.nan
            rel_vol = (volume / avg_vol_30d) if avg_vol_30d and avg_vol_30d > 0 else np.nan
            data.append(dict(
                Symbol=t.upper(), Price=price, PrevClose=prev_close, GapPct=gap_pct,
                Volume=volume, AvgVol30d=avg_vol_30d, RelVol=rel_vol,
                DayHigh=day_high, DayLow=day_low, Currency=currency
            ))
        except Exception:
            pass
    return pd.DataFrame(data)

@st.cache_data(ttl=45, show_spinner=False)
def get_intraday_5m_stats(tickers):
    import yfinance as yf
    out = []
    for t in tickers:
        try:
            y = yf.Ticker(t)
            df = y.history(period="1d", interval="5m", actions=False)
            if df.empty or "Volume" not in df:
                out.append(dict(Symbol=t.upper(), RelVol5m=np.nan, Vol5m=np.nan))
                continue
            last_vol = float(df["Volume"].iloc[-1])
            avg_5m_today = float(df["Volume"].iloc[:-1].mean()) if len(df) > 1 else np.nan
            rel5 = (last_vol / avg_5m_today) if avg_5m_today and avg_5m_today > 0 else np.nan
            out.append(dict(Symbol=t.upper(), RelVol5m=rel5, Vol5m=last_vol))
        except Exception:
            out.append(dict(Symbol=t.upper(), RelVol5m=np.nan, Vol5m=np.nan))
    return pd.DataFrame(out)

if not raw_tickers:
    st.info("Add some tickers in the sidebar.")
    st.stop()

with st.spinner("Fetching data…"):
    daily = get_daily_snapshot(raw_tickers)
    if daily.empty:
        st.error("No data returned. Try different tickers.")
        st.stop()
    if show_intraday:
        intraday = get_intraday_5m_stats(daily["Symbol"].tolist())
        df = daily.merge(intraday, on="Symbol", how="left")
    else:
        df = daily.copy()

# Filter & sort
df = df[df["Price"].between(min_price, max_price, inclusive="both")]
df = df[df["GapPct"] >= min_gap]
df = df[df["RelVol"].fillna(0) >= min_rel_vol]
df = df.sort_values(["GapPct", "RelVol"], ascending=[False, False]).reset_index(drop=True)

# Present
ren = {"RelVol":"Rel Vol (30d)", "RelVol5m":"Rel Vol (5m)", "GapPct":"Gap %", "AvgVol30d":"Avg Vol 30d", "PrevClose":"Prev Close", "Vol5m":"Vol 5m"}
view = df.rename(columns=ren)

st.subheader("Scanner")
st.dataframe(
    view[["Symbol","Price","Volume","Rel Vol (30d)","Rel Vol (5m)","Gap %","DayHigh","DayLow","Prev Close","Avg Vol 30d","Vol 5m","Currency"]],
    use_container_width=True,
    height=520
)

if refresh and refresh > 0:
    st.caption(f"Auto-refreshing every {refresh}s …")
    time.sleep(refresh)
    st.rerun()
