"""
Nifty 50 Chart Viewer — Streamlit app.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date

from utils.data_fetcher import fetch_stock_data
from utils.chart_builder import build_chart, build_rsi_plot, add_indicators
from utils.pushya_dates import get_pushya_pairs_in_range, filter_data_for_pushya_days
from utils.week_comparison import (
    get_week_comparison_data,
    build_week_comparison_chart,
    get_month_comparison_data,
    build_month_comparison_chart,
)

TICKER = "^NSEI"

PERIOD_DAYS = {
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
    "2 Years": 730,
}

st.set_page_config(
    page_title="Nifty 50 Chart Viewer",
    page_icon="📈",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
# Initialize variables
show_week_comparison = False
week_comparison_years = []
week_month = 2
week_number = 2
show_month_comparison = False
month_comparison_years = []
month = 2

with st.sidebar:
    st.header("Settings")
    st.text_input("Ticker", value=TICKER, disabled=True)
    st.caption("For NSE stocks add .NS (e.g. RELIANCE.NS). For Nifty use ^NSEI, for Sensex use ^BSESN")

    st.subheader("Technical Indicators")
    show_wap = st.checkbox("Show WAP/VWAP", value=False)
    show_ema = st.checkbox("Show EMA", value=False)
    ema_period = None
    if show_ema:
        ema_period = st.number_input("EMA period", min_value=2, max_value=500, value=70, step=1)

    show_fib = st.checkbox("Show Fibonacci retracement", value=False)
    fib_direction = "Low to High"
    if show_fib:
        fib_direction = st.selectbox("Fibonacci direction", ["Low to High", "High to Low"])

    st.divider()
    st.subheader("Week Comparison (5 Years)")
    show_week_comparison = st.checkbox("Compare same week across 5 years", value=False)
    
    if show_week_comparison:
        week_month = st.selectbox("Select Month", options=list(range(1, 13)), format_func=lambda x: datetime(2024, x, 1).strftime('%B'), index=1, key="week_month")  # February default
        week_number = st.selectbox("Select Week", options=[1, 2, 3, 4, 5], format_func=lambda x: f"Week {x}", index=1, key="week_number")  # Second week default
        current_year = datetime.now().year
        week_comparison_years = st.multiselect(
            "Select Years (up to 5)",
            options=list(range(current_year - 4, current_year + 1)),
            default=[current_year - 4, current_year - 3, current_year - 2, current_year - 1, current_year],
            max_selections=5,
            key="week_years",
        )
    
    st.divider()
    st.subheader("Month Comparison (5 Years)")
    show_month_comparison = st.checkbox("Compare same month across 5 years", value=False)
    
    if show_month_comparison:
        month = st.selectbox("Select Month", options=list(range(1, 13)), format_func=lambda x: datetime(2024, x, 1).strftime('%B'), index=1, key="month_month")  # February default
        current_year = datetime.now().year
        month_comparison_years = st.multiselect(
            "Select Years (up to 5)",
            options=list(range(current_year - 4, current_year + 1)),
            default=[current_year - 4, current_year - 3, current_year - 2, current_year - 1, current_year],
            max_selections=5,
            key="month_years",
        )
    
    st.divider()
    st.subheader("Pushya Nakshatra View")
    show_pushya_view = st.checkbox("Show Pushya Nakshatra dates", value=False)

    period_choice = st.selectbox(
        "Select Period",
        options=list(PERIOD_DAYS.keys()) + ["Custom Range"],
        index=3,  # 1 Year
    )

    start_date = None
    end_date = None
    date_error = None

    if period_choice == "Custom Range":
        end_default = datetime.now().date()
        start_default = end_default - timedelta(days=180)
        custom_start = st.date_input("Start date", value=start_default, key="custom_start")
        custom_end = st.date_input("End date", value=end_default, key="custom_end")
        if custom_start > custom_end:
            date_error = "Start date must be before or equal to end date."
            st.error(date_error)
        else:
            start_date = custom_start
            end_date = custom_end
    else:
        days = PERIOD_DAYS[period_choice]
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

    load_clicked = st.button("Load Chart", type="primary")

# ---------------------------------------------------------------------------
# Compute whether we should load and what range to use
# ---------------------------------------------------------------------------
if load_clicked and date_error:
    st.session_state["nifty_range"] = None
elif load_clicked and start_date is not None and end_date is not None:
    st.session_state["nifty_range"] = (start_date, end_date)

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
st.title("Nifty 50 Chart Viewer")

# Check if month comparison is enabled (doesn't need Load Chart)
if show_month_comparison and month_comparison_years:
    st.title("Nifty 50 Month Comparison")
    with st.spinner(f"Loading month comparison data for {len(month_comparison_years)} years..."):
        month_df = get_month_comparison_data(TICKER, month, month_comparison_years)
    
    if month_df is None or month_df.empty:
        st.error(f"Could not load data for the selected month. Please check your connection and try again.")
        st.info(f"Trying to fetch: {datetime(2024, month, 1).strftime('%B')} for years {month_comparison_years}")
    else:
        month_name = datetime(2024, month, 1).strftime('%B')
        st.success(f"✓ Loaded data for {month_name} across {len(month_comparison_years)} years")
        
        # Show summary table
        st.subheader(f"OHLCV Summary - {month_name}")
        summary_rows = []
        for year in sorted(month_comparison_years):
            year_data = month_df[month_df['Year'] == year]
            if not year_data.empty:
                latest = year_data.iloc[-1]
                summary_rows.append({
                    "Year": year,
                    "Date": latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)[:10],
                    "Open": round(latest['Open'], 2),
                    "High": round(latest['High'], 2),
                    "Low": round(latest['Low'], 2),
                    "Close": round(latest['Close'], 2),
                    "Volume": int(latest['Volume']),
                })
        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Show comparison charts - 1 chart per row (vertical stacking)
        comparison_figs = build_month_comparison_chart(month_df, month, "Nifty 50")
        if comparison_figs:
            st.subheader(f"Monthly Comparison - {month_name}")
            
            # Display charts vertically (1 chart per row)
            for fig in comparison_figs:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "scrollZoom": True,  # Mouse wheel zoom
                        "doubleClick": "reset",
                        "modeBarButtonsToAdd": [
                            "zoom2d",
                            "pan2d",
                            "select2d",
                            "lasso2d",
                            "zoomIn2d",
                            "zoomOut2d",
                            "autoScale2d",
                            "resetScale2d",
                        ],
                        "displayModeBar": True,
                        "displaylogo": False,
                    }
                )
        else:
            st.warning("Could not build comparison charts.")
    
    st.stop()  # Stop here if month comparison is active

# Check if week comparison is enabled (doesn't need Load Chart)
if show_week_comparison and week_comparison_years:
    st.title("Nifty 50 Week Comparison")
    with st.spinner(f"Loading week comparison data for {len(week_comparison_years)} years..."):
        week_df = get_week_comparison_data(TICKER, week_month, week_number, week_comparison_years)
    
    if week_df is None or week_df.empty:
        st.error(f"Could not load data for the selected week. Please check your connection and try again.")
        st.info(f"Trying to fetch: {datetime(2024, week_month, 1).strftime('%B')} Week {week_number} for years {week_comparison_years}")
    else:
        month_name = datetime(2024, week_month, 1).strftime('%B')
        st.success(f"✓ Loaded data for {month_name} Week {week_number} across {len(week_comparison_years)} years")
        
        # Show summary table
        st.subheader(f"OHLCV Summary - {month_name} Week {week_number}")
        summary_rows = []
        for year in sorted(week_comparison_years):
            year_data = week_df[week_df['Year'] == year]
            if not year_data.empty:
                latest = year_data.iloc[-1]
                summary_rows.append({
                    "Year": year,
                    "Date": latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)[:10],
                    "Open": round(latest['Open'], 2),
                    "High": round(latest['High'], 2),
                    "Low": round(latest['Low'], 2),
                    "Close": round(latest['Close'], 2),
                    "Volume": int(latest['Volume']),
                })
        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Show comparison charts side by side
        comparison_figs = build_week_comparison_chart(week_df, week_month, week_number, "Nifty 50")
        if comparison_figs:
            st.subheader(f"Side-by-Side Comparison - {month_name} Week {week_number}")
            
            # Create columns for side-by-side display (up to 5 columns)
            num_charts = len(comparison_figs)
            if num_charts == 1:
                cols = [st.columns(1)[0]]
            elif num_charts == 2:
                cols = st.columns(2)
            elif num_charts == 3:
                cols = st.columns(3)
            elif num_charts == 4:
                cols = st.columns(4)
            else:  # 5 charts
                cols = st.columns(5)
            
            for idx, fig in enumerate(comparison_figs):
                with cols[idx % len(cols)]:
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={
                            "scrollZoom": True,  # Mouse wheel zoom
                            "doubleClick": "reset",
                            "modeBarButtonsToAdd": [
                                "zoom2d",
                                "pan2d",
                                "select2d",
                                "lasso2d",
                                "zoomIn2d",
                                "zoomOut2d",
                                "autoScale2d",
                                "resetScale2d",
                            ],
                            "displayModeBar": True,
                            "displaylogo": False,
                        }
                    )
        else:
            st.warning("Could not build comparison charts.")
    
    st.stop()  # Stop here if week comparison is active

if "nifty_range" not in st.session_state or st.session_state["nifty_range"] is None:
    st.info("Select a period in the sidebar and click **Load Chart** to view the Nifty 50 chart.")
    st.stop()

start_date, end_date = st.session_state["nifty_range"]

# Validate date range
if start_date >= end_date:
    st.error("Invalid date range: Start date must be before end date.")
    st.stop()

# Test yfinance connection first
with st.spinner("Testing connection to Yahoo Finance..."):
    try:
        import yfinance as yf
        test_ticker = yf.Ticker("^NSEI")
        test_info = test_ticker.info
        if test_info:
            st.success("✓ Connected to Yahoo Finance")
    except Exception as e:
        st.warning(f"⚠ Connection test failed: {str(e)}")
        st.info("This might be a temporary issue. Trying to fetch data anyway...")

with st.spinner("Loading Nifty 50 data..."):
    df = fetch_stock_data(TICKER, start_date, end_date)

if df is None or df.empty:
    st.error(f"Could not load data for Nifty 50 (^NSEI) for date range {start_date} to {end_date}.")
    
    # Try alternative approaches
    st.info("🔍 Trying alternative methods...")
    
    # Method 1: Try with period instead of dates
    try:
        import yfinance as yf
        test_ticker = yf.Ticker("^NSEI")
        # Try fetching with period parameter
        test_data = test_ticker.history(period="1mo")
        if test_data is not None and not test_data.empty:
            st.success("✓ Successfully fetched data using period method!")
            # Filter to requested date range
            test_data = test_data[(test_data.index.date >= start_date) & (test_data.index.date <= end_date)]
            if not test_data.empty:
                df = test_data[["Open", "High", "Low", "Close", "Volume"]].copy()
                st.success("Data loaded successfully!")
            else:
                st.warning("Period method worked but no data in requested range.")
        else:
            raise Exception("Period method returned empty")
    except Exception as e1:
        st.warning(f"Period method failed: {str(e1)}")
        
        # Method 2: Try adjusted date range
        try:
            end_date_adj = end_date + timedelta(days=2)
            start_date_adj = start_date - timedelta(days=2)
            df = fetch_stock_data(TICKER, start_date_adj, end_date_adj)
            if df is not None and not df.empty:
                # Filter to original range
                df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]
                if not df.empty:
                    st.success("Data loaded with adjusted date range!")
                else:
                    df = None
        except Exception as e2:
            st.warning(f"Adjusted range method failed: {str(e2)}")
    
    if df is None or df.empty:
        st.error("❌ All methods failed. Troubleshooting steps:")
        st.info("1. **Check internet connection** - yfinance needs internet access")
        st.info("2. **Try a different date range** - Select 'Custom Range' with dates from at least 1 week ago")
        st.info("3. **Check yfinance version** - Run: `pip install --upgrade yfinance`")
        st.info("4. **Wait and retry** - Yahoo Finance API might be temporarily unavailable")
        st.info("5. **Try a longer period** - Select '1 Year' or '2 Years' instead of '1 Month'")
        
        with st.expander("🔧 Advanced: Test yfinance directly"):
            st.code("""
# Test in Python terminal:
import yfinance as yf
ticker = yf.Ticker("^NSEI")
data = ticker.history(period="1mo")
print(data.head())
            """)
        st.stop()

# Pushya Nakshatra filtering (only if data is loaded successfully)
pushya_pairs = []
selected_pushya_pair = None
if show_pushya_view and df is not None and not df.empty:
    try:
        pushya_pairs = get_pushya_pairs_in_range(start_date, end_date)
        if pushya_pairs:
            # Create dropdown options in main panel
            pushya_options = [
                f"{pair[0].strftime('%Y-%m-%d')} (Day Before) → {pair[1].strftime('%Y-%m-%d')} (Pushya)"
                for pair in pushya_pairs
            ]
            selected_idx = st.selectbox(
                "Select Pushya Nakshatra occurrence:",
                options=range(len(pushya_pairs)),
                format_func=lambda i: pushya_options[i],
                key="pushya_select"
            )
            selected_pushya_pair = pushya_pairs[selected_idx]
            # Filter data for selected Pushya dates
            df_pushya, requested_dates, found_dates = filter_data_for_pushya_days(df, selected_pushya_pair[1], include_day_before=True)
            
            # Check if we need to fetch more data around these dates
            missing_dates = [d for d in requested_dates if d not in found_dates]
            
            if missing_dates and len(found_dates) < len(requested_dates):
                # Try to fetch data specifically for the missing dates
                st.info(f"📅 Fetching additional data for missing dates...")
                try:
                    from utils.data_fetcher import fetch_stock_data
                    # Fetch wider range around Pushya dates (5 days before to 5 days after)
                    fetch_start = selected_pushya_pair[0] - timedelta(days=5)
                    fetch_end = selected_pushya_pair[1] + timedelta(days=5)
                    df_extra = fetch_stock_data(TICKER, fetch_start, fetch_end)
                    
                    if df_extra is not None and not df_extra.empty:
                        # Try filtering again with the extra data
                        df_pushya_retry, _, found_dates_retry = filter_data_for_pushya_days(df_extra, selected_pushya_pair[1], include_day_before=True)
                        if df_pushya_retry is not None and len(found_dates_retry) > len(found_dates):
                            df_pushya = df_pushya_retry
                            found_dates = found_dates_retry
                            st.success(f"✓ Found additional data!")
                except Exception as e:
                    st.warning(f"Could not fetch additional data: {str(e)}")
            
            if df_pushya is not None and not df_pushya.empty:
                df = df_pushya
                # Show which dates are actually available
                available_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in sorted(found_dates)])
                missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in sorted(missing_dates)]) if missing_dates else None
                
                if len(found_dates) == len(requested_dates) and found_dates == requested_dates:
                    st.success(f"📅 Showing data for **Day Before Pushya** ({selected_pushya_pair[0]}) and **Pushya Day** ({selected_pushya_pair[1]}) - Both days available!")
                else:
                    st.info(f"📅 Showing data for **Day Before Pushya** ({selected_pushya_pair[0]}) and **Pushya Day** ({selected_pushya_pair[1]})")
                    st.success(f"✓ Available dates: {available_dates_str} ({len(df)} candle(s))")
                    if missing_dates_str:
                        # Check if we're showing nearest trading days
                        if len(found_dates) == 2:
                            st.info(f"ℹ Note: {missing_dates_str} had no market data (weekend/holiday). Showing nearest trading days instead.")
                        else:
                            st.warning(f"⚠ Missing dates (likely weekends/holidays): {missing_dates_str}")
            else:
                st.warning(f"No market data available for Pushya dates: {selected_pushya_pair[0]} and {selected_pushya_pair[1]}. These might be weekends or market holidays.")
                st.info("Showing full date range instead.")
        else:
            st.info("No Pushya Nakshatra dates found in the selected date range. Try a longer period (e.g., 1 Year or 2 Years).")
    except Exception as e:
        st.warning(f"Error processing Pushya Nakshatra dates: {str(e)}")
        st.info("Showing full date range instead.")

# Summary table: latest Open, High, Low, Close, Volume
if show_pushya_view and selected_pushya_pair:
    st.subheader(f"OHLCV for Pushya Nakshatra: {selected_pushya_pair[0]} → {selected_pushya_pair[1]}")
    # Show both days if available
    summary_data = []
    for idx, row in df.iterrows():
        day_label = idx.date() if hasattr(idx, 'date') else str(idx)[:10]
        if day_label == selected_pushya_pair[0]:
            label = f"Day Before Pushya ({day_label})"
        elif day_label == selected_pushya_pair[1]:
            label = f"Pushya Day ({day_label})"
        else:
            label = str(day_label)
        summary_data.append({
            "Date": label,
            "Open": round(row["Open"], 2),
            "High": round(row["High"], 2),
            "Low": round(row["Low"], 2),
            "Close": round(row["Close"], 2),
            "Volume": int(row["Volume"]),
        })
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    latest = df.iloc[-1]
    st.subheader("Latest OHLCV")
    summary = latest[["Open", "High", "Low", "Close", "Volume"]].to_frame().T
    summary.index = ["Latest"]
    summary["Open"] = round(summary["Open"], 2)
    summary["High"] = round(summary["High"], 2)
    summary["Low"] = round(summary["Low"], 2)
    summary["Close"] = round(summary["Close"], 2)
    summary["Volume"] = int(summary["Volume"].iloc[0])
    st.dataframe(summary, use_container_width=True)

# Candlestick + Volume + MACD chart
if show_pushya_view and selected_pushya_pair:
    title = f"Nifty 50 (^NSEI) — Pushya: {selected_pushya_pair[0]} → {selected_pushya_pair[1]}"
else:
    title = f"Nifty 50 (^NSEI) — {start_date} to {end_date}"
fig = build_chart(
    df,
    title=title,
    show_vwap=show_wap,
    ema_period=int(ema_period) if ema_period is not None else None,
    show_fibonacci=show_fib,
    fibonacci_direction=fib_direction,
)
if fig is not None:
    # Configure Plotly chart with better zoom controls
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,  # Enable mouse wheel zoom
            "doubleClick": "reset",  # Double-click to reset zoom
            "modeBarButtonsToAdd": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"],
            "displayModeBar": True,
            "displaylogo": False,
        }
    )
else:
    st.warning("Could not build the main chart.")

# RSI chart
df_with_indicators = add_indicators(df.copy())
rsi_title = "RSI (14) — Nifty 50"
if show_pushya_view and selected_pushya_pair:
    rsi_title = f"RSI (14) — Pushya: {selected_pushya_pair[0]} → {selected_pushya_pair[1]}"
rsi_fig = build_rsi_plot(df_with_indicators, title=rsi_title)
if rsi_fig is not None:
    st.plotly_chart(
        rsi_fig,
        use_container_width=True,
        config={
            "scrollZoom": True,  # Enable mouse wheel zoom
            "doubleClick": "reset",
            "modeBarButtonsToAdd": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"],
            "displayModeBar": True,
            "displaylogo": False,
        }
    )
else:
    st.warning("Could not build the RSI chart.")
