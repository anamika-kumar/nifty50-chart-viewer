"""
Week comparison utilities for comparing the same week across multiple years.
"""

from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
import pandas as pd

# Type hint for Plotly Figure (avoid circular import)
try:
    from plotly.graph_objects import Figure
except ImportError:
    Figure = None


def get_week_dates(year: int, month: int, week_number: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a specific trading week (Monday to Friday) in a given year and month.
    Weeks can span across months - includes days from adjacent months if part of the week.
    
    Week 1 = First Monday to First Friday (may include days from previous month)
    Week 2 = Second Monday to Second Friday
    Week 3 = Third Monday to Third Friday
    Week 4 = Fourth Monday to Fourth Friday
    Week 5 = Fifth Monday to Fifth Friday (may include days from next month)
    
    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
        week_number: Week number in the month (1-5)
    
    Returns:
        Tuple of (start_date, end_date) for that trading week (Monday, Friday)
        Dates may be from adjacent months if the week spans month boundaries
    """
    # Get first day of the month
    first_day = date(year, month, 1)
    
    # Find the first Monday of the month
    # weekday(): Monday=0, Tuesday=1, ..., Sunday=6
    days_until_monday = (7 - first_day.weekday()) % 7
    if days_until_monday == 7:
        days_until_monday = 0
    
    first_monday = first_day + timedelta(days=days_until_monday)
    
    # If first Monday is not in this month (happens when month starts on Sunday)
    # Include the Monday from previous month if it's part of Week 1
    if first_monday.month != month:
        if week_number == 1:
            # Week 1: Use the Monday from previous month
            # This Monday is the start of Week 1 for this month
            nth_monday = first_monday
        else:
            # For other weeks, move to next Monday in this month
            nth_monday = first_monday + timedelta(days=7)
            # Calculate the Nth Monday
            nth_monday = nth_monday + timedelta(days=(week_number - 2) * 7)
    else:
        # First Monday is in this month
        # Calculate the Nth Monday (week_number = 1 means first Monday)
        nth_monday = first_monday + timedelta(days=(week_number - 1) * 7)
    
    # Friday is 4 days after Monday (Monday + 4 days = Friday)
    nth_friday = nth_monday + timedelta(days=4)
    
    # Allow dates to span across months - don't restrict to the selected month
    # This ensures we capture the full trading week even if it crosses month boundaries
    
    return nth_monday, nth_friday


def get_week_comparison_data(
    ticker: str,
    month: int,
    week_number: int,
    years: List[int],
) -> Optional[pd.DataFrame]:
    """
    Fetch data for the same week across multiple years.
    Weeks can span across months - fetches full week including adjacent month days.
    
    Args:
        ticker: Stock ticker symbol
        month: Month (1-12)
        week_number: Week number in month (1-5)
        years: List of years to fetch (e.g., [2022, 2023, 2024, 2025])
    
    Returns:
        DataFrame with data for all years, with a 'Year' column added
    """
    from utils.data_fetcher import fetch_stock_data
    
    all_data = []
    
    for year in years:
        try:
            week_start, week_end = get_week_dates(year, month, week_number)
            # Fetch data with a small buffer to ensure we get all trading days
            # Add 2 days before and after to account for weekends/holidays
            fetch_start = week_start - timedelta(days=2)
            fetch_end = week_end + timedelta(days=2)
            
            df = fetch_stock_data(ticker, fetch_start, fetch_end)
            
            if df is not None and not df.empty:
                df = df.copy()
                # Filter to only include the actual week dates (Monday to Friday)
                mask = (df.index.date >= week_start) & (df.index.date <= week_end)
                df = df[mask].copy()
                
                if not df.empty:
                    df['Year'] = year
                    all_data.append(df)
        except Exception:
            continue
    
    if not all_data:
        return None
    
    # Combine all data
    combined = pd.concat(all_data, ignore_index=False)
    return combined


def build_week_comparison_chart(
    df: pd.DataFrame,
    month: int,
    week_number: int,
    title_prefix: str = "Nifty 50",
) -> List:
    """
    Build separate comparison charts for each year, showing the same week.
    Returns a list of figures (one per year).
    
    Args:
        df: DataFrame with OHLCV data and 'Year' column
        month: Month number
        week_number: Week number
        title_prefix: Prefix for chart title
    
    Returns:
        List of Plotly Figure objects (one per year)
    """
    import plotly.graph_objects as go
    
    if df is None or df.empty or 'Year' not in df.columns:
        return []
    
    years = sorted(df['Year'].unique())
    month_name = datetime(2024, month, 1).strftime('%B')
    figures = []
    
    for year in years:
        year_data = df[df['Year'] == year].copy()
        if year_data.empty:
            continue
        
        # Create single figure for candlestick only (no volume)
        fig = go.Figure()
        
        # Price chart (candlestick) - green/red colors
        fig.add_trace(
            go.Candlestick(
                x=year_data.index,
                open=year_data['Open'],
                high=year_data['High'],
                low=year_data['Low'],
                close=year_data['Close'],
                name=f"{year}",
                increasing_line_color="green",
                increasing_fillcolor="green",
                decreasing_line_color="red",
                decreasing_fillcolor="red",
                line=dict(width=1.5),
            )
        )
        
        # Update layout with vertical zoom enabled (title positioned below toolbar to avoid overlap)
        fig.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(t=100),
            dragmode="zoom",
            hovermode="x unified",
            xaxis_rangeslider_visible=False,
            title=dict(
                text=f"{title_prefix} - {year}",
                y=0.88,
                yanchor="top",
                yref="container",
            ),
        )
        
        # Configure axes
        fig.update_yaxes(
            title_text="Price",
            tickformat=",",
            fixedrange=False,  # Enable vertical zoom
        )
        
        # Configure x-axis to show dates with day of week
        fig.update_xaxes(
            tickformat="%a %Y-%m-%d",  # Abbreviated day name + date (e.g., "Mon 2025-02-10")
            tickangle=-45,
        )
        
        figures.append(fig)
    
    return figures


def get_month_comparison_data(
    ticker: str,
    month: int,
    years: List[int],
) -> Optional[pd.DataFrame]:
    """
    Fetch data for the same month across multiple years.
    
    Args:
        ticker: Stock ticker symbol
        month: Month (1-12)
        years: List of years to fetch (e.g., [2022, 2023, 2024, 2025])
    
    Returns:
        DataFrame with data for all years, with a 'Year' column added
    """
    from utils.data_fetcher import fetch_stock_data
    
    all_data = []
    
    for year in years:
        try:
            # Get first and last day of the month
            if month == 12:
                month_start = date(year, 12, 1)
                month_end = date(year, 12, 31)
            else:
                month_start = date(year, month, 1)
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            
            df = fetch_stock_data(ticker, month_start, month_end)
            
            if df is not None and not df.empty:
                df = df.copy()
                df['Year'] = year
                all_data.append(df)
        except Exception:
            continue
    
    if not all_data:
        return None
    
    # Combine all data
    combined = pd.concat(all_data, ignore_index=False)
    return combined


def build_month_comparison_chart(
    df: pd.DataFrame,
    month: int,
    title_prefix: str = "Nifty 50",
) -> List:
    """
    Build separate comparison charts for each year, showing the same month.
    Returns a list of figures (one per year). No volume chart.
    
    Args:
        df: DataFrame with OHLCV data and 'Year' column
        month: Month number
        title_prefix: Prefix for chart title
    
    Returns:
        List of Plotly Figure objects (one per year)
    """
    import plotly.graph_objects as go
    
    if df is None or df.empty or 'Year' not in df.columns:
        return []
    
    years = sorted(df['Year'].unique())
    month_name = datetime(2024, month, 1).strftime('%B')
    figures = []
    
    for year in years:
        year_data = df[df['Year'] == year].copy()
        if year_data.empty:
            continue
        
        # Create single figure for candlestick only (no volume)
        fig = go.Figure()
        
        # Price chart (candlestick) - green/red colors
        fig.add_trace(
            go.Candlestick(
                x=year_data.index,
                open=year_data['Open'],
                high=year_data['High'],
                low=year_data['Low'],
                close=year_data['Close'],
                name=f"{year}",
                increasing_line_color="green",
                increasing_fillcolor="green",
                decreasing_line_color="red",
                decreasing_fillcolor="red",
                line=dict(width=1.5),
            )
        )
        
        # Update layout with vertical zoom enabled (title positioned below toolbar to avoid overlap)
        fig.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(t=100),
            dragmode="zoom",
            hovermode="x unified",
            xaxis_rangeslider_visible=False,
            title=dict(
                text=f"{title_prefix} - {year} ({month_name})",
                y=0.88,
                yanchor="top",
                yref="container",
            ),
        )
        
        # Configure axes
        fig.update_yaxes(
            title_text="Price",
            tickformat=",",
            fixedrange=False,  # Enable vertical zoom
        )
        
        # Configure x-axis to show dates with day of week
        fig.update_xaxes(
            tickformat="%a %Y-%m-%d",  # Abbreviated day name + date (e.g., "Mon 2025-02-10")
            tickangle=-45,
        )
        
        figures.append(fig)
    
    return figures
