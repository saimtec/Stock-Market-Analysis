import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import time
import warnings
warnings.filterwarnings('ignore')

# Page setup
st.set_page_config(
    page_title="Stock Market Analysis",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { padding: 2rem; background: linear-gradient(180deg, #0b1220 0%, #0f172a 45%, #111827 100%); color: #e5e7eb; }
    .stApp { background: linear-gradient(180deg, #0b1220 0%, #0f172a 45%, #111827 100%); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background-color: #111827; }
    [data-testid="stSidebar"] * { color: #e5e7eb; }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 10px; }
    .stAlert { border-radius: 10px; }
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
    h1 { color: #f8fafc; text-align: center; margin-bottom: 1rem; }
    h2 { color: #bfdbfe; margin-top: 1.5rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }
    .hero-card {
        background: linear-gradient(135deg, rgba(30,58,138,0.35), rgba(17,24,39,0.95));
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 20px;
    }
    .hero-title { color: #f8fafc; font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }
    .hero-subtitle { color: #cbd5e1; margin: 0 0 12px 0; }
    .hero-grid { display: grid; grid-template-columns: repeat(2, minmax(200px, 1fr)); gap: 8px 14px; }
    .hero-item { color: #e2e8f0; font-weight: 500; background: rgba(15,23,42,0.7); border: 1px solid #334155; border-radius: 10px; padding: 8px 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("Stock Market Analysis Dashboard")
st.markdown("""
    <div class="hero-card">
        <div class="hero-title">Real-time Stock Analysis with Technical Indicators</div>
        <p class="hero-subtitle">Analyze live market movement, trend momentum, and short-term direction from one dashboard.</p>
        <div class="hero-grid">
            <div class="hero-item">Live market data from Yahoo Finance with automatic fallback</div>
            <div class="hero-item">Technical indicators: SMA, RSI, and MACD</div>
            <div class="hero-item">Volume analysis and multi-stock performance comparison</div>
            <div class="hero-item">30-day trend projection for educational insights</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None
if 'data_source' not in st.session_state:
    st.session_state.data_source = None


def fetch_stock_data(symbol: str, period: str):
    required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}

    def map_period_to_days(selected_period: str):
        period_days = {
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
            '5y': 1825
        }
        return period_days.get(selected_period, 180)

    def fetch_from_stooq(ticker: str, selected_period: str):
        stooq_symbol = ticker.lower()
        if '.' not in stooq_symbol:
            stooq_symbol = f"{stooq_symbol}.us"

        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
        data = pd.read_csv(url)
        if data.empty or 'Date' not in data.columns:
            return None

        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        data = data.set_index('Date').sort_index()

        cutoff_days = map_period_to_days(selected_period)
        cutoff_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=cutoff_days)
        data = data.loc[data.index >= cutoff_date]

        if data.empty:
            return None
        return data

    def normalize(df: pd.DataFrame):
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if not required_cols.issubset(set(df.columns)):
            return None
        cleaned = df.dropna(subset=['Close']).copy()
        return cleaned if not cleaned.empty else None

    def fetch_yahoo_with_retry(ticker: str, selected_period: str):
        for attempt in range(3):
            try:
                primary = normalize(yf.download(ticker, period=selected_period, progress=False, threads=False, timeout=20))
                if primary is not None:
                    return primary, "Yahoo Finance (download)"
            except Exception:
                pass

            try:
                fallback = normalize(yf.Ticker(ticker).history(period=selected_period, auto_adjust=False))
                if fallback is not None:
                    return fallback, "Yahoo Finance (history)"
            except Exception:
                pass

            time.sleep(1.0 + attempt)
        return None, None

    yahoo_data, yahoo_source = fetch_yahoo_with_retry(symbol, period)
    if yahoo_data is not None:
        return yahoo_data, yahoo_source

    try:
        stooq_fallback = normalize(fetch_from_stooq(symbol, period))
        if stooq_fallback is not None:
            return stooq_fallback, "Stooq CSV fallback"
    except Exception:
        pass

    return None, None

# STEP 1: DATA FETCH
st.header("Step 1: Select and Fetch Stock Data")
col1, col2, col3, col4 = st.columns(4)

with col1:
    stock_symbol = st.text_input("Stock Symbol", value="AAPL", help="e.g., AAPL, GOOGL").upper().strip()
with col2:
    period = st.selectbox("Time Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
with col3:
    st.write("")
    st.write("")
    fetch_btn = st.button("Fetch Data", use_container_width=True)
with col4:
    st.write("")
    st.write("")
    st.info("Real-time updates")

if fetch_btn and stock_symbol:
    try:
        with st.spinner(f"Fetching {stock_symbol}..."):
            stock_data, source = fetch_stock_data(stock_symbol, period)
            if stock_data is None or stock_data.empty:
                st.error(f"No data for {stock_symbol}. Data providers may be blocked or the symbol is invalid.")
                st.stop()
            st.session_state.stock_data = stock_data
            st.session_state.stock_symbol = stock_symbol
            st.session_state.data_source = source
            st.success(f"Data loaded for {stock_symbol} ({source})")
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.stop()

# DISPLAY DATA
if st.session_state.stock_data is not None:
    stock_data = st.session_state.stock_data.copy()
    stock_symbol = st.session_state.stock_symbol
    if st.session_state.data_source:
        st.caption(f"Active data source: {st.session_state.data_source}")
    
    # Flatten columns again if needed
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)
    
    # STEP 2: PRICE OVERVIEW
    st.header("Step 2: Price Overview")
    
    close_series = stock_data['Close']
    latest_price = float(close_series.iloc[-1])
    previous_price = float(close_series.iloc[-2]) if len(close_series) > 1 else latest_price
    price_change = latest_price - previous_price
    price_change_pct = (price_change / previous_price * 100) if previous_price != 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Current Price", f"${latest_price:.2f}", f"${price_change:.2f}")
    with col2:
        direction = "UP" if price_change >= 0 else "DOWN"
        st.metric("Day Change", f"${price_change:.2f}", f"{direction} {price_change_pct:.2f}%")
    with col3:
        high_val = float(close_series.max())
        st.metric("Period High", f"${high_val:.2f}")
    with col4:
        low_val = float(close_series.min())
        st.metric("Period Low", f"${low_val:.2f}")
    with col5:
        avg_vol = float(stock_data['Volume'].mean()) / 1e6
        st.metric("Avg Volume", f"{avg_vol:.2f}M")
    
    # STEP 3: TECHNICAL INDICATORS
    st.header("Step 3: Price Chart and Technical Indicators")
    
    stock_data['SMA_20'] = close_series.rolling(window=20).mean()
    stock_data['SMA_50'] = close_series.rolling(window=50).mean()
    
    def calculate_rsi(data, window=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    stock_data['RSI'] = calculate_rsi(close_series)
    exp1 = close_series.ewm(span=12, adjust=False).mean()
    exp2 = close_series.ewm(span=26, adjust=False).mean()
    stock_data['MACD'] = exp1 - exp2
    stock_data['Signal'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()
    stock_data['Histogram'] = stock_data['MACD'] - stock_data['Signal']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        show_sma = st.checkbox("Show SMA (20, 50)", value=True)
    with col2:
        show_rsi = st.checkbox("Show RSI(14)", value=False)
    with col3:
        show_macd = st.checkbox("Show MACD", value=False)
    
    # Price chart
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(stock_data.index, close_series, label='Close Price', color='black', linewidth=2.5)
    if show_sma:
        ax.plot(stock_data.index, stock_data['SMA_20'], label='SMA 20', alpha=0.7, color='blue')
        ax.plot(stock_data.index, stock_data['SMA_50'], label='SMA 50', alpha=0.7, color='orange')
    ax.set_title(f'{stock_symbol} - Price Chart', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()
    
    if show_rsi:
        fig, ax = plt.subplots(figsize=(15, 4))
        ax.plot(stock_data.index, stock_data['RSI'], label='RSI(14)', color='purple', linewidth=2)
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought (70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold (30)')
        ax.fill_between(stock_data.index, 30, 70, alpha=0.1)
        ax.set_title(f'{stock_symbol} - RSI Indicator', fontsize=14, fontweight='bold')
        ax.set_ylabel('RSI')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()
    
    if show_macd:
        fig, ax = plt.subplots(figsize=(15, 4))
        ax.plot(stock_data.index, stock_data['MACD'], label='MACD', color='blue')
        ax.plot(stock_data.index, stock_data['Signal'], label='Signal', color='red')
        ax.bar(stock_data.index, stock_data['Histogram'], label='Histogram', alpha=0.3)
        ax.set_title(f'{stock_symbol} - MACD', fontsize=14, fontweight='bold')
        ax.set_ylabel('MACD')
        ax.axhline(y=0, color='black', alpha=0.3)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()
    
    # STEP 4: VOLUME ANALYSIS
    st.header("Step 4: Volume Analysis")
    
    fig, ax = plt.subplots(figsize=(15, 4))
    close_vals = close_series.values
    colors = ['green' if i > 0 and close_vals[i] >= close_vals[i-1] else 'red' for i in range(len(close_vals))]
    colors[0] = 'gray'
    ax.bar(stock_data.index, stock_data['Volume'], color=colors, alpha=0.6)
    ax.set_title(f'{stock_symbol} - Trading Volume', fontsize=14, fontweight='bold')
    ax.set_ylabel('Volume')
    ax.set_xlabel('Date')
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_v = float(stock_data['Volume'].mean()) / 1e6
        st.metric("Avg Volume", f"{avg_v:.2f}M")
    with col2:
        max_v = float(stock_data['Volume'].max()) / 1e6
        st.metric("Max Volume", f"{max_v:.2f}M")
    with col3:
        cur_v = float(stock_data['Volume'].iloc[-1]) / 1e6
        st.metric("Current Volume", f"{cur_v:.2f}M")
    
    # STEP 5: TREND PROJECTION
    st.header("Step 5: Price Trend and Forecast")
    
    X = np.arange(len(stock_data))
    y = close_series.values.flatten()
    z = np.polyfit(X, y, 1)
    p = np.poly1d(z)
    trend_line = p(X)
    
    future_days = 30
    future_X = np.arange(len(stock_data), len(stock_data) + future_days)
    future_prices = p(future_X)
    last_date = stock_data.index[-1]
    forecast_dates = pd.date_range(start=last_date, periods=future_days+1, freq='D')[1:]
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(stock_data.index, close_series, label='Historical', color='black', linewidth=2.5)
    ax.plot(stock_data.index, trend_line, label='Trend', color='blue', linestyle='--', linewidth=2)
    ax.plot(forecast_dates, future_prices, label='Forecast (30d)', color='orange', linestyle='--', linewidth=2.5)
    ax.fill_between(forecast_dates, future_prices * 0.95, future_prices * 1.05, alpha=0.2, color='orange', label='+-5%')
    ax.set_title(f'{stock_symbol} - 30-Day Forecast', fontsize=14, fontweight='bold')
    ax.set_ylabel('Price ($)')
    ax.set_xlabel('Date')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()
    
    st.subheader("Forecast Summary")
    current_price = float(close_series.iloc[-1])
    forecast_price = float(future_prices[-1])
    forecast_change = ((forecast_price - current_price) / current_price) * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Price", f"${current_price:.2f}")
    with col2:
        st.metric("Forecasted (30d)", f"${forecast_price:.2f}")
    with col3:
        direction = "UP" if forecast_change >= 0 else "DOWN"
        st.metric("Change", f"{direction} {forecast_change:.2f}%")
    
    st.warning("Educational only - Not financial advice. Research before trading.")
    
    # STEP 6: PORTFOLIO COMPARISON
    st.header("Step 6: Compare Multiple Stocks")
    col1, col2 = st.columns(2)
    with col1:
        compare_symbols = st.multiselect("Select stocks", ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'], default=['AAPL', 'GOOGL'])
    with col2:
        comparison_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], key='comp_period')
    
    if st.button("Compare Stocks", use_container_width=True):
        if compare_symbols:
            comparison_data = {}
            for symbol in compare_symbols:
                try:
                    data, _ = fetch_stock_data(symbol, comparison_period)
                    if data is not None and not data.empty:
                        ret = (float(data['Close'].iloc[-1]) / float(data['Close'].iloc[0]) - 1) * 100
                        comparison_data[symbol] = ret
                except:
                    st.warning(f"Could not fetch {symbol}")
            
            if comparison_data:
                fig, ax = plt.subplots(figsize=(12, 6))
                symbols = list(comparison_data.keys())
                returns = list(comparison_data.values())
                colors = ['green' if r >= 0 else 'red' for r in returns]
                ax.barh(symbols, returns, color=colors, alpha=0.7)
                ax.set_xlabel('Return (%)')
                ax.set_title(f'Performance Comparison ({comparison_period})', fontsize=14, fontweight='bold')
                ax.axvline(x=0, color='black', linestyle='-')
                ax.grid(True, alpha=0.3, axis='x')
                for i, v in enumerate(returns):
                    ax.text(v, i, f' {v:.2f}%', va='center', fontweight='bold')
                plt.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close()
                
                df = pd.DataFrame({'Stock': symbols, 'Return (%)': [f'{r:.2f}%' for r in returns], 'Performance': ['Gain' if r >= 0 else 'Loss' for r in returns]})
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    # STEP 7: STATISTICAL ANALYSIS
    st.header("Step 7: Statistical Analysis")
    daily_returns = close_series.pct_change().dropna()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Volatility", f"{float(daily_returns.std()):.4f}")
    with col2:
        st.metric("Avg Daily Return", f"{float(daily_returns.mean()):.4f}")
    with col3:
        st.metric("Skewness", f"{float(daily_returns.skew()):.4f}")
    with col4:
        st.metric("Kurtosis", f"{float(daily_returns.kurtosis()):.4f}")
    
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.hist(daily_returns, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    mean_val = float(daily_returns.mean())
    ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.4f}')
    ax.set_xlabel('Daily Return')
    ax.set_ylabel('Frequency')
    ax.set_title(f'{stock_symbol} - Returns Distribution', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

else:
    st.info("Enter stock symbol and click Fetch Data to start")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Popular Stocks")
        st.markdown("- AAPL - Apple\n- GOOGL - Google\n- MSFT - Microsoft\n- AMZN - Amazon\n- TSLA - Tesla")
    with col2:
        st.subheader("Tips")
        st.markdown("- Use 1-3 months if rate limited\n- Forecasts are educational\n- Refresh for latest data")