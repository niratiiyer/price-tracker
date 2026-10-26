"""Crypto market monitor dashboard.  Run locally with:  streamlit run dashboard.py"""
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

from tracker.fmt import money
from tracker.rules import move_threshold_pct
from tracker.storage import ALERTS_FILE, PRICES_FILE, WATCHLIST_FILE

TZ = "America/New_York"

st.set_page_config(page_title="Crypto Market Monitor", layout="wide")
st.title("Crypto Market Monitor")
st.caption(
    f"Prices from CoinGecko, checked automatically every hour. Alerts fire when a price crosses one of your "
    f"levels or moves more than {move_threshold_pct():g}% between two checks."
)

watchlist = pd.read_csv(WATCHLIST_FILE)
if not PRICES_FILE.exists():
    st.info("No prices recorded yet. The first automatic check will fill this in.")
    st.stop()

prices = pd.read_csv(PRICES_FILE, parse_dates=["checked_at"])
prices["checked_at"] = prices["checked_at"].dt.tz_convert(TZ)
alerts = pd.DataFrame(columns=["checked_at", "coin_id", "symbol", "kind", "price", "detail"])
if ALERTS_FILE.exists():
    alerts = pd.read_csv(ALERTS_FILE, parse_dates=["checked_at"])
    alerts["checked_at"] = alerts["checked_at"].dt.tz_convert(TZ)

latest = prices.sort_values("checked_at").groupby("coin_id").tail(1).set_index("coin_id")
last_check = prices["checked_at"].max()
week_ago = last_check - timedelta(days=7)

# --- headline numbers ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Coins watched", len(watchlist))
col2.metric("Price checks recorded", f"{prices['checked_at'].nunique():,}")
col3.metric("Unusual moves flagged (7 days)", int(((alerts["kind"] == "move") & (alerts["checked_at"] >= week_ago)).sum()))
col4.metric("Last checked", last_check.strftime("%b %-d, %-I:%M %p"))

# --- current prices ---
rows = []
for c in watchlist.itertuples():
    if c.coin_id not in latest.index:
        continue
    now = latest.loc[c.coin_id]
    below = c.alert_below if pd.notna(c.alert_below) else None
    above = c.alert_above if pd.notna(c.alert_above) else None
    if below is not None and now.price <= below:
        status = "Below your level"
    elif above is not None and now.price >= above:
        status = "Above your level"
    else:
        status = "Within range"
    rows.append({
        "Coin": f"{c.name} ({c.symbol})",
        "Price": money(now.price),
        "Since last check": now.change_since_last_pct / 100 if pd.notna(now.change_since_last_pct) else None,
        "24h": now.change_24h_pct / 100,
        "Alert below": money(below) if below is not None else "",
        "Alert above": money(above) if above is not None else "",
        "Status": status,
    })
pct_cols = {c: st.column_config.NumberColumn(format="percent") for c in ["Since last check", "24h"]}
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config=pct_cols)

# --- chart ---
st.subheader("Price history")
names = {f"{c.name} ({c.symbol})": c for c in watchlist.itertuples()}
choice = st.selectbox("Coin", list(names))
coin = names[choice]
one = prices[prices["coin_id"] == coin.coin_id]

line = (
    alt.Chart(one)
    .mark_line(point=alt.OverlayMarkDef(size=18))
    .encode(
        x=alt.X("checked_at:T", title=None),
        y=alt.Y("price:Q", title="Price (USD)", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("checked_at:T", title="Checked", format="%b %d %I:%M %p"),
                 alt.Tooltip("price:Q", title="Price", format="$,.4~f"),
                 alt.Tooltip("change_since_last_pct:Q", title="Change since last check (%)", format="+.2f")],
    )
)
levels = pd.DataFrame(
    [{"level": v, "kind": k} for k, v in [("Alert below", coin.alert_below), ("Alert above", coin.alert_above)] if pd.notna(v)]
)
chart = line
if not levels.empty:
    chart = line + alt.Chart(levels).mark_rule(strokeDash=[6, 4]).encode(
        y="level:Q",
        color=alt.Color("kind:N", title=None, scale=alt.Scale(domain=["Alert below", "Alert above"], range=["#d62728", "#2ca02c"])),
    )
st.altair_chart(chart, use_container_width=True)

# --- biggest moves and alert log ---
left, right = st.columns(2)
with left:
    st.subheader("Biggest moves between checks")
    moves = prices.dropna(subset=["change_since_last_pct"]).copy()
    if moves.empty:
        st.write("Needs at least two checks.")
    else:
        moves["size"] = moves["change_since_last_pct"].abs()
        top = moves.nlargest(10, "size")
        st.dataframe(
            pd.DataFrame({
                "When": top["checked_at"].dt.strftime("%b %-d, %-I:%M %p"),
                "Coin": top["symbol"],
                "Move": top["change_since_last_pct"] / 100,
                "Price after": top["price"].map(money),
            }),
            hide_index=True, use_container_width=True,
            column_config={"Move": st.column_config.NumberColumn(format="percent")},
        )
with right:
    st.subheader("Alert log")
    if alerts.empty:
        st.write("No alerts yet.")
    else:
        labels = {"below": "Fell below level", "above": "Rose above level", "move": "Unusual move"}
        recent = alerts.sort_values("checked_at", ascending=False).head(20)
        st.dataframe(
            pd.DataFrame({
                "When": recent["checked_at"].dt.strftime("%b %-d, %-I:%M %p"),
                "Coin": recent["symbol"],
                "Alert": recent["kind"].map(labels),
                "Price": recent["price"].map(money),
                "Detail": recent["detail"],
            }),
            hide_index=True, use_container_width=True,
        )

with st.expander("How to add coins or change alert levels"):
    st.markdown(
        "Edit `watchlist.csv`. Format: `coin_id,symbol,name,alert_below,alert_above`\n\n"
        "Example: `cardano,ADA,Cardano,0.50,0.80`\n\n"
        "`coin_id` is on the coin's CoinGecko page."
    )
