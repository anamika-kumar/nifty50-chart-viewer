"""
Pushya Nakshatra date lookup and utilities.
Pushya Nakshatra occurs approximately every 27 days as the Moon cycles through the 27 nakshatras.
"""

from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
import pandas as pd

# Pushya Nakshatra dates (approximate, based on Indian Standard Time)
# These are the dates when Pushya Nakshatra is active (typically starts in the evening/next day)
# Format: (year, month, day) - represents the main day of Pushya
PUSHYA_DATES = [
    # 2024
    (2024, 1, 25), (2024, 2, 21), (2024, 3, 19), (2024, 4, 16), (2024, 5, 13),
    (2024, 6, 9), (2024, 7, 7), (2024, 8, 3), (2024, 8, 30), (2024, 9, 26),
    (2024, 10, 24), (2024, 11, 20), (2024, 12, 18),
    # 2025
    (2025, 1, 14), (2025, 2, 10), (2025, 3, 9), (2025, 4, 6), (2025, 5, 3),
    (2025, 5, 30), (2025, 6, 27), (2025, 7, 24), (2025, 8, 21), (2025, 9, 17),
    (2025, 10, 14), (2025, 11, 10), (2025, 12, 8),
    # 2026 (estimated - add more as needed)
    (2026, 1, 4), (2026, 1, 31), (2026, 2, 27), (2026, 3, 26), (2026, 4, 22),
    (2026, 5, 19), (2026, 6, 15), (2026, 7, 13), (2026, 8, 9), (2026, 9, 5),
    (2026, 10, 3), (2026, 10, 30), (2026, 11, 26), (2026, 12, 24),
]


def get_pushya_dates_in_range(start_date: date, end_date: date) -> List[date]:
    """
    Get all Pushya Nakshatra dates within a given date range.
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        List of dates (date objects) when Pushya Nakshatra occurs
    """
    pushya_list = []
    for year, month, day in PUSHYA_DATES:
        pushya_date = date(year, month, day)
        if start_date <= pushya_date <= end_date:
            pushya_list.append(pushya_date)
    return sorted(pushya_list)


def get_pushya_pairs_in_range(start_date: date, end_date: date) -> List[Tuple[date, date]]:
    """
    Get pairs of (day_before_pushya, pushya_date) for all Pushya occurrences in range.
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        List of tuples: [(day_before, pushya_date), ...]
    """
    pushya_dates = get_pushya_dates_in_range(start_date, end_date)
    pairs = []
    for pushya_date in pushya_dates:
        day_before = pushya_date - timedelta(days=1)
        # Only include if day_before is within range and is a weekday (market day)
        if day_before >= start_date and day_before.weekday() < 5:  # Monday=0, Friday=4
            pairs.append((day_before, pushya_date))
    return pairs


def filter_data_for_pushya_days(
    df: pd.DataFrame,
    pushya_date: date,
    include_day_before: bool = True,
    use_nearest_trading_days: bool = True,
) -> Tuple[Optional[pd.DataFrame], List[date], List[date]]:
    """
    Filter DataFrame to include the day before Pushya and/or Pushya day.
    If exact dates aren't available and use_nearest_trading_days=True,
    will find the nearest trading days.
    
    Args:
        df: DataFrame with datetime index
        pushya_date: The Pushya Nakshatra date
        include_day_before: If True, include the day before Pushya
        use_nearest_trading_days: If True, use nearest trading days if exact dates missing
        
    Returns:
        Tuple of:
        - Filtered DataFrame or None if no data found
        - List of requested dates (original)
        - List of dates actually found in data
    """
    if df is None or df.empty:
        return None, [], []
    
    # Ensure index is datetime
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df.index = pd.to_datetime(df.index)
    
    dates_to_include = [pushya_date]
    if include_day_before:
        day_before = pushya_date - timedelta(days=1)
        dates_to_include.insert(0, day_before)  # Put day_before first
    
    # Get available dates in the dataframe (sorted)
    available_dates = sorted([idx.date() for idx in df.index])
    
    # Try to find exact dates first
    dates_to_fetch = dates_to_include.copy()
    
    # If exact dates not found and use_nearest_trading_days, find nearest
    if use_nearest_trading_days:
        dates_to_fetch = []
        for target_date in dates_to_include:
            if target_date in available_dates:
                dates_to_fetch.append(target_date)
            else:
                # Find nearest trading day (before or after, prefer before for day_before, after for pushya)
                nearest = None
                # Try to find nearest date
                for avail_date in available_dates:
                    if target_date == dates_to_include[0]:  # day_before - prefer date before or equal
                        if avail_date <= target_date:
                            if nearest is None or avail_date > nearest:
                                nearest = avail_date
                    else:  # pushya_date - prefer date after or equal
                        if avail_date >= target_date:
                            nearest = avail_date
                            break
                        elif nearest is None or avail_date > nearest:
                            nearest = avail_date
                
                if nearest:
                    dates_to_fetch.append(nearest)
                else:
                    dates_to_fetch.append(target_date)  # Keep original if nothing found
    
    # Filter by date (ignore time component)
    # Normalize dates to compare properly
    dates_to_fetch_pd = [pd.Timestamp(d).normalize() for d in dates_to_fetch]
    
    # Create mask by comparing normalized dates
    mask = df.index.normalize().isin(dates_to_fetch_pd)
    
    filtered = df[mask].copy()
    
    # Get which dates were actually found
    found_dates = sorted([idx.date() for idx in filtered.index]) if not filtered.empty else []
    
    if filtered.empty:
        return None, dates_to_include, found_dates
    return filtered, dates_to_include, found_dates
