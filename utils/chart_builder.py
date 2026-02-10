"""
Chart rendering module using Plotly and optional mplfinance/pandas-ta.
"""

import io
import pandas as pd
import mplfinance as mpf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List, Any, Dict, Tuple
import matplotlib
matplotlib.use("Agg")

FIB_LEVELS: List[Tuple[float, str]] = [
    (0.0, "0%"),
    (0.236, "23.6%"),
    (0.382, "38.2%"),
    (0.5, "50%"),
    (0.618, "61.8%"),
    (0.786, "78.6%"),
    (1.0, "100%"),
]


def _add_vwap(df: pd.DataFrame, col_name: str = "VWAP") -> pd.DataFrame:
    """
    Add a simple cumulative VWAP/WAP line over the selected date range.
    Typical Price = (High + Low + Close) / 3
    VWAP = cumsum(TypicalPrice * Volume) / cumsum(Volume)
    """
    if df is None or df.empty:
        return df
    if not all(c in df.columns for c in ["High", "Low", "Close", "Volume"]):
        return df
    vol = df["Volume"].fillna(0)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    denom = vol.cumsum()
    df[col_name] = (tp.mul(vol).cumsum() / denom).where(denom != 0)
    return df


def _add_ema(df: pd.DataFrame, period: int, col_name: Optional[str] = None) -> pd.DataFrame:
    """Add an EMA(period) column using pandas-ta if available, else pandas ewm."""
    if df is None or df.empty or "Close" not in df.columns:
        return df
    if not isinstance(period, int) or period <= 0:
        return df
    col = col_name or f"EMA_{period}"
    try:
        import pandas_ta as ta

        df[col] = ta.ema(df["Close"], length=period)
    except Exception:
        df[col] = df["Close"].ewm(span=period, adjust=False).mean()
    return df


def _fib_prices(high_price: float, low_price: float, direction: str) -> Dict[str, float]:
    """
    Compute Fibonacci retracement prices for a range [low_price, high_price].

    direction:
      - "Low to High": retracements measured down from the High
      - "High to Low": retracements measured up from the Low
    """
    if high_price is None or low_price is None:
        return {}
    if high_price == low_price:
        return {}
    rng = float(high_price - low_price)
    out: Dict[str, float] = {}
    if direction == "High to Low":
        # Downtrend: bounce levels up from low
        for r, label in FIB_LEVELS:
            out[label] = float(low_price + rng * r)
    else:
        # Uptrend: pullback levels down from high
        for r, label in FIB_LEVELS:
            out[label] = float(high_price - rng * r)
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add RSI, MACD, and SMAs to an OHLCV DataFrame using pandas-ta.

    Appends columns:
      - RSI (period 14)
      - MACD (fast=12, slow=26, signal=9) — MACD_* columns from pandas-ta
      - SMA_20 (20-day Simple Moving Average)
      - SMA_50 (50-day Simple Moving Average)

    Args:
        df: DataFrame with Open, High, Low, Close, Volume (or at least Close).

    Returns:
        The same DataFrame with the new indicator columns added.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return df
    try:
        import pandas_ta as ta
    except ImportError:
        return df

    close = df["Close"]

    df["RSI"] = ta.rsi(close, length=14)

    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None and isinstance(macd, pd.DataFrame):
        for col in macd.columns:
            df[col] = macd[col]

    df["SMA_20"] = ta.sma(close, length=20)
    df["SMA_50"] = ta.sma(close, length=50)

    return df


def add_ta_indicators(df: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
    """
    Add technical indicators using pandas-ta. Modifies df in place and returns it.
    """
    try:
        import pandas_ta as ta
    except ImportError:
        return df

    for ind in indicators:
        try:
            if ind == "SMA_20":
                df["SMA_20"] = ta.sma(df["Close"], length=20)
            elif ind == "SMA_50":
                df["SMA_50"] = ta.sma(df["Close"], length=50)
            elif ind == "EMA_12":
                df["EMA_12"] = ta.ema(df["Close"], length=12)
            elif ind == "EMA_26":
                df["EMA_26"] = ta.ema(df["Close"], length=26)
            elif ind == "BB":
                bb = ta.bbands(df["Close"], length=20, std=2)
                if bb is not None and isinstance(bb, pd.DataFrame):
                    df[bb.columns] = bb
            elif ind == "RSI":
                df["RSI"] = ta.rsi(df["Close"], length=14)
            elif ind == "MACD":
                macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
                if macd is not None and isinstance(macd, pd.DataFrame):
                    df[macd.columns] = macd
        except Exception:
            continue
    return df


def build_chart(
    df: pd.DataFrame,
    title: str = "Stock Chart",
    show_vwap: bool = False,
    ema_period: Optional[int] = None,
    show_fibonacci: bool = False,
    fibonacci_direction: str = "Low to High",
) -> Optional[go.Figure]:
    """
    Build an interactive Plotly figure: candlestick + SMA 20/50 overlay,
    volume subplot, and MACD subplot. Does not call fig.show().

    Expects df to have OHLCV; add_indicators() is called to ensure
    SMA_20, SMA_50, RSI, and MACD columns exist.

    Returns:
        A single plotly.graph_objects.Figure, or None if data is invalid.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return None

    plot_df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(plot_df.index):
        plot_df.index = pd.to_datetime(plot_df.index)
    plot_df = add_indicators(plot_df)
    if show_vwap:
        plot_df = _add_vwap(plot_df, col_name="VWAP")
    if ema_period is not None:
        plot_df = _add_ema(plot_df, int(ema_period), col_name=f"EMA_{int(ema_period)}")

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(title, "Volume", "MACD"),
    )

    # Row 1: Candlestick + SMA 20 + SMA 50
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    if "SMA_20" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["SMA_20"],
                name="SMA 20",
                line=dict(color="blue", width=1.5),
            ),
            row=1,
            col=1,
        )
    if "SMA_50" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["SMA_50"],
                name="SMA 50",
                line=dict(color="orange", width=1.5),
            ),
            row=1,
            col=1,
        )
    # Optional EMA overlay
    if ema_period is not None:
        ema_col = f"EMA_{int(ema_period)}"
        if ema_col in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=plot_df[ema_col],
                    name=f"EMA {int(ema_period)}",
                    line=dict(color="#8E44AD", width=1.5),
                ),
                row=1,
                col=1,
            )
    # Optional VWAP/WAP overlay
    if show_vwap and "VWAP" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["VWAP"],
                name="WAP/VWAP",
                line=dict(color="#2E86C1", width=1.2, dash="dot"),
            ),
            row=1,
            col=1,
        )

    # Optional Fibonacci retracement levels (based on range in selected window)
    if show_fibonacci and all(c in plot_df.columns for c in ["High", "Low"]):
        hi = float(plot_df["High"].max())
        lo = float(plot_df["Low"].min())
        fibs = _fib_prices(hi, lo, fibonacci_direction)
        for label, price in fibs.items():
            fig.add_hline(
                y=price,
                line_dash="dash",
                line_color="rgba(120,120,120,0.7)",
                annotation_text=f"Fib {label}: {price:,.2f}",
                annotation_position="top left",
                row=1,
                col=1,
            )

    # Row 2: Volume
    colors = ["red" if plot_df["Close"].iloc[i] < plot_df["Open"].iloc[i] else "green" for i in range(len(plot_df))]
    fig.add_trace(
        go.Bar(
            x=plot_df.index,
            y=plot_df["Volume"],
            name="Volume",
            marker_color=colors,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # Row 3: MACD — pandas-ta names: MACD_12_26_9 (line), MACDs_12_26_9 (signal), MACDh_12_26_9 (hist)
    macd_cols = [c for c in plot_df.columns if c.startswith("MACD")]
    macd_line_col = next((c for c in macd_cols if "MACDh" not in c and "MACDs" not in c), None)
    signal_col = next((c for c in macd_cols if "MACDs" in c), None)
    hist_col = next((c for c in macd_cols if "MACDh" in c), None)

    if macd_cols:
        if macd_line_col and macd_line_col in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=plot_df[macd_line_col],
                    name="MACD",
                    line=dict(color="blue", width=1.5),
                ),
                row=3,
                col=1,
            )
        if signal_col and signal_col in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=plot_df[signal_col],
                    name="Signal",
                    line=dict(color="orange", width=1),
                ),
                row=3,
                col=1,
            )
        if hist_col and hist_col in plot_df.columns:
            fig.add_trace(
                go.Bar(
                    x=plot_df.index,
                    y=plot_df[hist_col],
                    name="Histogram",
                    marker_color=plot_df[hist_col].apply(lambda v: "green" if v >= 0 else "red"),
                    showlegend=False,
                ),
                row=3,
                col=1,
            )

    # Get year range for legend
    if not plot_df.empty:
        years = sorted(set(plot_df.index.year))
        year_text = f"Year: {', '.join(map(str, years))}" if years else ""
    else:
        year_text = ""
    
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=750,  # Increased height to accommodate year legend
        # Enable mouse wheel zoom and improve zoom behavior
        dragmode="zoom",
        hovermode="x unified",
        # Add year annotation below x-axis
        annotations=[
            dict(
                text=year_text,
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.02,
                showarrow=False,
                font=dict(size=12, color="gray"),
                xanchor="center",
            )
        ] if year_text else [],
    )
    
    # Configure Y-axes with custom formatting (no 'k' suffix, show full numbers)
    fig.update_yaxes(
        title_text="Price",
        row=1,
        col=1,
        tickformat=",",  # Use comma separator, no 'k' abbreviation
        showspikes=True,
        spikemode="across",
    )
    fig.update_yaxes(
        title_text="Volume",
        row=2,
        col=1,
        tickformat=",",  # Use comma separator, no 'k' abbreviation
    )
    fig.update_yaxes(
        title_text="MACD",
        row=3,
        col=1,
        tickformat=",",  # Use comma separator
    )
    
    # Configure X-axis to show dates with day of week (applies to all subplots)
    # Determine appropriate tick interval based on data range
    if not plot_df.empty:
        date_range = (plot_df.index.max() - plot_df.index.min()).days
        if date_range <= 10:
            dtick_val = "D1"  # Daily for short ranges
        elif date_range <= 60:
            dtick_val = "D7"  # Weekly for medium ranges
        elif date_range <= 365:
            dtick_val = "M1"  # Monthly for year ranges
        else:
            dtick_val = "M3"  # Quarterly for longer ranges
    else:
        dtick_val = "D1"
    
    fig.update_xaxes(
        rangeslider_visible=False,
        showspikes=True,
        spikemode="across",
        tickformat="%a %Y-%m-%d",  # Show day of week + date (e.g., "Mon 2025-02-10")
        dtick=dtick_val,
        tickangle=-45,  # Angle labels for better readability
    )
    
    return fig


def build_rsi_figure(df: pd.DataFrame, title: str = "RSI") -> Optional[go.Figure]:
    """
    Build a Plotly figure for RSI: blue RSI line and horizontal dashed
    lines at 70 (overbought) and 30 (oversold). Does not call fig.show().

    Returns:
        A plotly.graph_objects.Figure, or None if RSI data is missing.
    """
    if df is None or df.empty or "RSI" not in df.columns:
        return None

    plot_df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(plot_df.index):
        plot_df.index = pd.to_datetime(plot_df.index)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_df.index,
            y=plot_df["RSI"],
            name="RSI (14)",
            line=dict(color="blue", width=2),
        )
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
    # Get year range for RSI chart legend
    if not plot_df.empty:
        years = sorted(set(plot_df.index.year))
        year_text = f"Year: {', '.join(map(str, years))}" if years else ""
    else:
        year_text = ""
    
    fig.update_layout(
        title=title,
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100], tickformat=","),  # No 'k' suffix
        template="plotly_white",
        height=350,  # Increased height to accommodate year legend
        showlegend=True,
        dragmode="zoom",  # Enable mouse wheel zoom
        hovermode="x unified",
        # Add year annotation below x-axis
        annotations=[
            dict(
                text=year_text,
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.02,
                showarrow=False,
                font=dict(size=12, color="gray"),
                xanchor="center",
            )
        ] if year_text else [],
    )
    
    # Configure X-axis to show dates with day of week
    fig.update_xaxes(
        tickformat="%a %Y-%m-%d",  # Show day of week + date (e.g., "Mon 2025-02-10")
        dtick="D1",  # Show every day
        tickangle=-45,  # Angle labels for better readability
    )
    
    return fig


def build_mpf_plot(
    df: pd.DataFrame,
    title: str = "Stock Chart",
    volume: bool = True,
    indicators: Optional[List[str]] = None,
) -> Optional[bytes]:
    """
    Build an OHLC/candlestick chart with optional volume and indicators.
    Returns PNG image as bytes for display in Streamlit.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return None

    # Ensure index is datetime
    plot_df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(plot_df.index):
        plot_df.index = pd.to_datetime(plot_df.index)

    # Add TA indicators if requested
    if indicators:
        plot_df = add_ta_indicators(plot_df, indicators)

    # Build mplfinance plot kwargs
    add_plot = []
    if "SMA_20" in plot_df.columns:
        add_plot.append(mpf.make_addplot(plot_df["SMA_20"], color="blue", width=0.7))
    if "SMA_50" in plot_df.columns:
        add_plot.append(mpf.make_addplot(plot_df["SMA_50"], color="orange", width=0.7))
    if "EMA_12" in plot_df.columns:
        add_plot.append(mpf.make_addplot(plot_df["EMA_12"], color="green", width=0.6))
    if "EMA_26" in plot_df.columns:
        add_plot.append(mpf.make_addplot(plot_df["EMA_26"], color="red", width=0.6))
    if "BBL_20_2.0" in plot_df.columns and "BBU_20_2.0" in plot_df.columns:
        add_plot.append(mpf.make_addplot(plot_df["BBL_20_2.0"], color="gray", width=0.5))
        add_plot.append(mpf.make_addplot(plot_df["BBU_20_2.0"], color="gray", width=0.5))

    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mpf.make_marketcolors(up="green", down="red", edge="inherit"),
        gridstyle="",
        y_on_right=True,
    )

    buf = io.BytesIO()
    mpf.plot(
        plot_df,
        type="candle",
        style=style,
        title=title,
        ylabel="Price",
        volume=volume,
        addplot=add_plot if add_plot else None,
        savefig=dict(fname=buf, dpi=100, bbox_inches="tight", format="png"),
    )
    buf.seek(0)
    return buf.read()


def build_rsi_plot(df: pd.DataFrame, title: str = "RSI") -> Optional[go.Figure]:
    """
    Build a Plotly figure for RSI (blue line, dashed 70/30 levels).
    Returns the same as build_rsi_figure for compatibility.
    """
    return build_rsi_figure(df, title=title)
