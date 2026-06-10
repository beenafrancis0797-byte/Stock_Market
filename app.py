import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import date, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #5DADE2;
    }
    .section-header {
        font-size: 18px; font-weight: 600;
        color: #1a1a2e; margin: 20px 0 10px;
        border-bottom: 2px solid #f0f0f0; padding-bottom: 6px;
    }
    .insight-box {
        background: #fff8e7; border-left: 4px solid #FAD7A0;
        border-radius: 8px; padding: 12px 16px; margin: 8px 0;
        font-size: 14px;
    }
    .up   { color: #16A34A; font-weight: 700; }
    .down { color: #DC2626; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────
POPULAR = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
           "META", "NVDA", "NFLX", "AMD", "INTC",
           "JPM", "BAC", "V", "MA", "PYPL"]
COLORS  = ["#2563EB", "#16A34A", "#D97706", "#DC2626",
           "#7C3AED", "#0891B2", "#DB2777", "#EA580C"]

# ── SIDEBAR ───────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/stock-market.png", width=60)
st.sidebar.title("Stock Dashboard")
st.sidebar.markdown("---")

# Stock selector
selected_stocks = st.sidebar.multiselect(
    "Select Stocks", POPULAR,
    default=["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
)

# Custom ticker input
custom = st.sidebar.text_input("Add custom ticker (e.g. RELIANCE.NS)", "")
if custom:
    selected_stocks.append(custom.upper().strip())

# Date range
st.sidebar.markdown("### Date Range")
start_date = st.sidebar.date_input("Start", date(2020, 1, 1))
end_date   = st.sidebar.date_input("End",   date(2024, 12, 31))

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown(
    "Live stock data powered by **Yahoo Finance**.\n\n"
    "Data updates every time you change filters."
)

if not selected_stocks:
    st.warning("Please select at least one stock from the sidebar.")
    st.stop()

# ── LOAD DATA ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data(tickers, start, end):
    raw     = yf.download(tickers, start=start, end=end, auto_adjust=True)
    if len(tickers) == 1:
        prices = raw["Close"].to_frame(name=tickers[0])
    else:
        prices = raw["Close"]
    return prices.dropna()

with st.spinner("Fetching live data from Yahoo Finance..."):
    prices = load_data(selected_stocks, str(start_date), str(end_date))

if prices.empty or len(prices) < 2:
    st.error("No data available for the selected stocks and date range. Please try different selections.")
    st.stop()

# Keep only columns with enough data
prices = prices.dropna(axis=1, thresh=10)
selected_stocks = [s for s in selected_stocks if s in prices.columns]

if not selected_stocks:
    st.error("No valid stock data found. Please try different tickers.")
    st.stop()

returns     = prices.pct_change().dropna()
cum_returns = (1 + returns).cumprod()

if cum_returns.empty or len(cum_returns) < 1:
    st.error("Not enough data to calculate returns. Please adjust your date range.")
    st.stop()

# ── TITLE ─────────────────────────────────────────────────────
st.title("📈 Stock Market Dashboard")
st.caption(f"Live data · Yahoo Finance · {start_date} → {end_date}")

# ── KPI ROW ───────────────────────────────────────────────────
cols = st.columns(len(selected_stocks))
for col, stock in zip(cols, selected_stocks):
    if stock not in prices.columns:
        col.metric(label=stock, value="N/A", delta="No data")
        continue
    stock_data = prices[stock].dropna()
    if len(stock_data) < 2:
        col.metric(label=stock, value="N/A", delta="Insufficient data")
        continue
    total_ret  = (stock_data.iloc[-1] / stock_data.iloc[0] - 1) * 100
    latest     = stock_data.iloc[-1]
    daily_ret  = returns[stock].dropna().iloc[-1] * 100 if len(returns[stock].dropna()) > 0 else 0
    col.metric(
        label=stock,
        value=f"${latest:.2f}",
        delta=f"{total_ret:.1f}% total return"
    )

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Returns", "🕯️ Candlestick", "🌡️ Correlation",
    "⚖️ Risk vs Return", "📉 Volatility"
])


# ══════════════════════════════════════════════
# TAB 1 — CUMULATIVE RETURNS
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Cumulative Returns</div>', unsafe_allow_html=True)

    fig = go.Figure()
    for stock, color in zip(selected_stocks, COLORS):
        if stock not in cum_returns.columns:
            continue
        fig.add_trace(go.Scatter(
            x=cum_returns.index,
            y=cum_returns[stock],
            name=stock,
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{stock}</b><br>Date: %{{x}}<br>Growth: %{{y:.2f}}x<extra></extra>"
        ))
    fig.update_layout(
        title="Growth of $1 Invested",
        yaxis_title="Portfolio Value ($)",
        xaxis_title="Date",
        template="simple_white",
        legend=dict(orientation="h", y=1.1),
        height=420,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Performance table
    st.markdown('<div class="section-header">Performance Summary</div>', unsafe_allow_html=True)
    annual_ret = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    sharpe     = annual_ret / annual_vol
    total      = cum_returns.iloc[-1] - 1 if len(cum_returns) > 0 else pd.Series(0, index=prices.columns)

    perf = pd.DataFrame({
        "Total Return":      total.map(lambda x: f"{x:.1%}"),
        "Annual Return":     annual_ret.map(lambda x: f"{x:.1%}"),
        "Annual Volatility": annual_vol.map(lambda x: f"{x:.1%}"),
        "Sharpe Ratio":      sharpe.map(lambda x: f"{x:.2f}"),
    })
    st.dataframe(perf, use_container_width=True)

    st.markdown(
        f'<div class="insight-box">🏆 <b>Best performer:</b> '
        f'{total.idxmax()} with {total.max():.1%} total return. '
        f'Best risk-adjusted: {sharpe.idxmax()} (Sharpe: {sharpe.max():.2f})</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════
# TAB 2 — CANDLESTICK
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">Candlestick Chart</div>', unsafe_allow_html=True)

    candle_stock = st.selectbox("Select stock for candlestick", selected_stocks)
    show_ma      = st.checkbox("Show Moving Averages (50 & 200 day)", value=True)

    @st.cache_data(ttl=3600)
    def load_ohlcv(ticker, start, end):
        return yf.download(ticker, start=start, end=end, auto_adjust=True)

    with st.spinner(f"Loading {candle_stock} OHLCV data..."):
        ohlcv = load_ohlcv(candle_stock, str(start_date), str(end_date))

    if not ohlcv.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=ohlcv.index,
            open=ohlcv["Open"].squeeze(),
            high=ohlcv["High"].squeeze(),
            low=ohlcv["Low"].squeeze(),
            close=ohlcv["Close"].squeeze(),
            increasing_line_color="#16A34A",
            decreasing_line_color="#DC2626",
            name=candle_stock
        ))

        if show_ma:
            close = ohlcv["Close"].squeeze()
            ma50  = close.rolling(50).mean()
            ma200 = close.rolling(200).mean()
            fig.add_trace(go.Scatter(
                x=ohlcv.index, y=ma50,
                name="50-day MA", line=dict(color="#FAD7A0", width=1.5, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=ohlcv.index, y=ma200,
                name="200-day MA", line=dict(color="#D2B4DE", width=1.5, dash="dash")
            ))

        fig.update_layout(
            title=f"{candle_stock} Price Chart",
            yaxis_title="Price ($)",
            template="simple_white",
            xaxis_rangeslider_visible=False,
            height=480,
            legend=dict(orientation="h", y=1.08)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Volume bar
        fig_vol = go.Figure()
        vol_colors = ["#A9DFBF" if c >= o else "#F1948A"
                      for c, o in zip(ohlcv["Close"].squeeze(), ohlcv["Open"].squeeze())]
        fig_vol.add_trace(go.Bar(
            x=ohlcv.index,
            y=ohlcv["Volume"].squeeze(),
            marker_color=vol_colors,
            name="Volume"
        ))
        fig_vol.update_layout(
            title=f"{candle_stock} Trading Volume",
            yaxis_title="Volume",
            template="simple_white",
            height=200,
            showlegend=False
        )
        st.plotly_chart(fig_vol, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 3 — CORRELATION
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Return Correlation Matrix</div>', unsafe_allow_html=True)

    if len(selected_stocks) < 2:
        st.info("Select at least 2 stocks to see correlation.")
    else:
        corr = returns.corr()

        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="Blues",
            zmin=-1, zmax=1,
            title="Stock Return Correlation",
            height=450
        )
        fig.update_layout(template="simple_white")
        st.plotly_chart(fig, use_container_width=True)

        high_corr = []
        for i in range(len(corr.columns)):
            for j in range(i+1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.7:
                    high_corr.append(
                        f"{corr.columns[i]} & {corr.columns[j]}: {val:.2f}"
                    )

        if high_corr:
            st.markdown(
                f'<div class="insight-box">⚠️ <b>High correlation pairs</b> (>0.7) — '
                f'poor for diversification: {", ".join(high_corr)}</div>',
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════
# TAB 4 — RISK vs RETURN
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Risk vs Return Analysis</div>', unsafe_allow_html=True)

    annual_ret2 = returns.mean() * 252
    annual_vol2 = returns.std() * np.sqrt(252)
    sharpe2     = annual_ret2 / annual_vol2

    fig = go.Figure()
    for stock, color in zip(selected_stocks, COLORS):
        if stock not in annual_ret2.index:
            continue
        fig.add_trace(go.Scatter(
            x=[annual_vol2[stock]],
            y=[annual_ret2[stock]],
            mode="markers+text",
            name=stock,
            text=[stock],
            textposition="top center",
            marker=dict(size=18, color=color,
                        line=dict(color="white", width=2)),
            hovertemplate=(
                f"<b>{stock}</b><br>"
                f"Risk: {annual_vol2[stock]:.1%}<br>"
                f"Return: {annual_ret2[stock]:.1%}<br>"
                f"Sharpe: {sharpe2[stock]:.2f}<extra></extra>"
            )
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Annual Risk vs Return (Higher right = better return, Lower = less risk)",
        xaxis_title="Annual Volatility (Risk)",
        yaxis_title="Annual Return",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        template="simple_white",
        showlegend=False,
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

    # Sharpe ratio bar
    sharpe_df = sharpe2.reset_index()
    sharpe_df.columns = ["Stock", "Sharpe"]
    sharpe_df = sharpe_df.sort_values("Sharpe", ascending=False)

    fig2 = px.bar(
        sharpe_df, x="Stock", y="Sharpe",
        color="Sharpe", color_continuous_scale="Blues",
        title="Sharpe Ratio by Stock (Higher = Better Risk-Adjusted Return)",
        height=300
    )
    fig2.update_layout(template="simple_white", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 5 — VOLATILITY
# ══════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-header">Rolling Volatility</div>', unsafe_allow_html=True)

    window = st.slider("Rolling window (days)", 10, 90, 30)

    rolling_vol = returns.rolling(window).std() * np.sqrt(252)

    fig = go.Figure()
    for stock, color in zip(selected_stocks, COLORS):
        if stock not in rolling_vol.columns:
            continue
        fig.add_trace(go.Scatter(
            x=rolling_vol.index,
            y=rolling_vol[stock],
            name=stock,
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{stock}</b><br>Vol: %{{y:.1%}}<extra></extra>"
        ))
    fig.update_layout(
        title=f"{window}-Day Rolling Annualised Volatility",
        yaxis_title="Volatility",
        yaxis_tickformat=".0%",
        template="simple_white",
        legend=dict(orientation="h", y=1.1),
        height=420,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'<div class="insight-box">📌 <b>Volatility spikes</b> indicate market stress periods. '
        f'Compare peaks across stocks to identify which are most sensitive to market events.</div>',
        unsafe_allow_html=True
    )
