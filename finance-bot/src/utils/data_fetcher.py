"""
Data fetching utilities for stock market analysis
"""
import pandas as pd
from datetime import date, timedelta
from typing import Optional

try:
    from ..fetcher.fetcher_factory import FetcherFactory
except ImportError:
    # Fallback for when running as script
    from fetcher.fetcher_factory import FetcherFactory


async def fetch_extended_historical(ticker: str, days: int = 250, verbose: bool = True):
    """
    Fetch extended historical data for pivot analysis
    Note: 250 days = ~1 year of trading days (accounting for weekends/holidays)
    
    Args:
        ticker: Stock symbol
        days: Number of days to fetch (default 250 for ~1 year)
        verbose: If True, print progress messages
    
    Returns:
        DataFrame with historical data, or None if fetch failed
    """
    if verbose:
        print(f"🔍 Fetching extended historical data for {ticker}...")
    
    try:
        # Create VNStock fetcher
        fetcher = FetcherFactory.create_fetcher('vnstock', rate_limit=60)
        
        # Get today's date and specified days back
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        if verbose:
            print(f"📅 Fetching data from {start_date} to {end_date} (~{days} days)")
        
        # Fetch historical data
        historical_df = await fetcher.fetch_historical(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            interval='1D'
        )
        
        if historical_df.empty:
            if verbose:
                print(f"❌ No historical data found for {ticker}")
            return None
        
        # Sort by date and reset index
        historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
        
        if verbose:
            print(f"✅ Fetched {len(historical_df)} historical records")
            print(f"📊 Data columns: {list(historical_df.columns)}")
            
            # Show latest data
            latest_data = historical_df.iloc[-1]
            print(f"\n📈 Latest {ticker} Data:")
            print(f"   Date: {latest_data['timestamp'].strftime('%Y-%m-%d')}")
            print(f"   Open: {latest_data['open']:,.2f}")
            print(f"   High: {latest_data['high']:,.2f}")
            print(f"   Low: {latest_data['low']:,.2f}")
            print(f"   Close: {latest_data['close']:,.2f}")
            print(f"   Volume: {latest_data['volume']:,.0f}")
        
        return historical_df
        
    except Exception as e:
        if verbose:
            print(f"❌ Error fetching extended historical data: {e}")
            import traceback
            traceback.print_exc()
        return None


async def get_current_price(ticker: str, historical_close: Optional[float] = None, verbose: bool = True):
    """
    Get current real-time price
    
    Args:
        ticker: Stock symbol
        historical_close: Historical close price for validation
        verbose: If True, print progress messages
    
    Returns:
        Current price or None if unavailable
    """
    try:
        fetcher = FetcherFactory.create_fetcher('vnstock', rate_limit=60)
        realtime_data = await fetcher.fetch_realtime([ticker])
        
        if realtime_data and len(realtime_data) > 0:
            current_price = realtime_data[0].close
            
            # Validate price format - VNStock might return prices in different units
            # If real-time price is way different from historical, use historical instead
            if historical_close and historical_close > 0:
                price_ratio = current_price / historical_close
                # If price differs by more than 10x, likely wrong unit
                if price_ratio > 10 or price_ratio < 0.1:
                    if verbose:
                        print(f"⚠️  Real-time price ({current_price:,.2f}) seems inconsistent with historical ({historical_close:,.2f})")
                        print(f"    Using historical close price instead")
                    return historical_close
            
            if verbose:
                print(f"✅ Current price for {ticker}: {current_price:,.2f}")
            return current_price
        else:
            if verbose:
                print(f"⚠️  Real-time price unavailable for {ticker}, will use latest historical close")
            return None
            
    except Exception as e:
        if verbose:
            print(f"⚠️  Error fetching real-time price: {e}, will use latest historical close")
        return None

