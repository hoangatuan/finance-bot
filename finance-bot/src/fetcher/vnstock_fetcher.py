"""
VNStock fetcher implementation
"""
import asyncio
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, date, timedelta
import pandas as pd
from vnstock import Quote, Trading
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_fetcher import BaseFetcher, StockData


class VNStockFetcher(BaseFetcher):
    """VNStock data fetcher for Vietnamese stock market"""
    
    # Valid sources for VNStock API
    VALID_SOURCES = ['VCI']
    
    def __init__(self, rate_limit: int = 60, default_source: str = 'VCI'):
        super().__init__(rate_limit)
        self.min_interval = 60.0 / rate_limit  # seconds between requests
        self.default_source = default_source if default_source in self.VALID_SOURCES else 'VCI'
        
    async def _rate_limit_wait(self):
        """Wait to respect rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        self.last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_historical(
        self, 
        ticker: str, 
        start_date: Union[str, date], 
        end_date: Union[str, date],
        interval: str = '1D',
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch historical data for a ticker
        
        Args:
            ticker: Stock symbol (e.g., 'VNM', 'HPG')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Time interval ('1m', '5m', '15m', '30m', '1H', '1D', '1W', '1M')
            source: Data source ('VCI', 'TCBS', 'MSN'). If None, uses default_source
            
        Returns:
            DataFrame with standardized columns
        """
        await self._rate_limit_wait()
        
        if not self.validate_interval(interval):
            raise ValueError(f"Unsupported interval: {interval}")
        
        # Use provided source or default
        source_to_use = source if source in self.VALID_SOURCES else self.default_source
        
        try:
            # Create Quote object with valid source
            quote = Quote(symbol=ticker, source=source_to_use)
            
            # Convert dates to string if needed
            start_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
            end_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)
            
            # Fetch data
            raw_data = quote.history(
                start=start_str,
                end=end_str,
                interval=interval,
                to_df=True
            )
            
            if raw_data.empty:
                print(f"No historical data found for {ticker} from {source_to_use}")
                return pd.DataFrame()
            
            # Normalize data
            normalized_data = self.normalize_data(raw_data, ticker, 'historical')
            normalized_data['interval'] = interval
            normalized_data['source_detail'] = source_to_use
            
            return normalized_data
            
        except Exception as e:
            print(f"Error fetching historical data for {ticker} from {source_to_use}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_realtime(self, tickers: List[str]) -> List[StockData]:
        """
        Fetch real-time data for multiple tickers
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            List of StockData objects
        """
        await self._rate_limit_wait()
        
        try:
            # Fetch real-time data
            trading = Trading()
            raw_data = trading.price_board(symbols_list=tickers)
            
            if raw_data.empty:
                return []
            
            # Convert to standardized format
            stock_data_list = []
            
            for ticker in tickers:
                ticker_data = raw_data[raw_data[('listing', 'symbol')] == ticker]
                
                if not ticker_data.empty:
                    # Extract key data
                    match_price = ticker_data[('match', 'match_price')].iloc[0]
                    match_vol = ticker_data[('match', 'match_vol')].iloc[0]
                    highest = ticker_data[('match', 'highest')].iloc[0]
                    lowest = ticker_data[('match', 'lowest')].iloc[0]
                    accumulated_vol = ticker_data[('match', 'accumulated_volume')].iloc[0]
                    
                    # Create StockData object
                    stock_data = StockData(
                        ticker=ticker,
                        timestamp=datetime.now(),
                        open=0,  # Real-time data doesn't have open
                        high=highest,
                        low=lowest,
                        close=match_price,
                        volume=match_vol,
                        source='vnstock',
                        data_type='realtime',
                        interval='1m'
                    )
                    
                    stock_data_list.append(stock_data)
            
            return stock_data_list
            
        except Exception as e:
            print(f"Error fetching real-time data: {e}")
            raise
    
    def normalize_data(self, raw_data: pd.DataFrame, ticker: str, data_type: str) -> pd.DataFrame:
        """
        Normalize raw VNStock data to standard format
        
        Args:
            raw_data: Raw data from VNStock API
            ticker: Stock symbol
            data_type: 'historical' or 'realtime'
            
        Returns:
            Normalized DataFrame
        """
        if raw_data.empty:
            return pd.DataFrame()
        
        # Create copy to avoid modifying original
        df = raw_data.copy()
        
        # Rename columns to standard format
        column_mapping = {
            'time': 'timestamp',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }
        
        # Rename columns if they exist
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Add metadata columns
        df['ticker'] = ticker
        df['source'] = 'vnstock'
        df['data_type'] = data_type
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Select and reorder columns
        standard_columns = [
            'ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'source', 'data_type'
        ]
        
        # Only include columns that exist
        existing_columns = [col for col in standard_columns if col in df.columns]
        df = df[existing_columns]
        
        return df
    
    async def fetch_with_interval(
        self,
        ticker: str,
        interval: str = '1D',
        days_back: int = 30,
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch data with specific interval and days back
        
        Args:
            ticker: Stock symbol
            interval: Time interval
            days_back: Number of days to go back
            source: Data source ('VCI', 'TCBS', 'MSN')
            
        Returns:
            DataFrame with historical data
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        return await self.fetch_historical(ticker, start_date, end_date, interval, source)
    
    async def fetch_from_multiple_sources(
        self,
        ticker: str,
        start_date: Union[str, date],
        end_date: Union[str, date],
        interval: str = '1D'
    ) -> pd.DataFrame:
        """
        Try to fetch data from multiple sources if one fails
        
        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Time interval
            
        Returns:
            DataFrame with data from first successful source
        """
        for source in self.VALID_SOURCES:
            try:
                data = await self.fetch_historical(ticker, start_date, end_date, interval, source)
                if not data.empty:
                    print(f"Successfully fetched data for {ticker} from {source}")
                    return data
            except Exception as e:
                print(f"Failed to fetch from {source}: {e}")
                continue
        
        # If all sources fail, return empty DataFrame
        print(f"All sources failed for {ticker}")
        return pd.DataFrame()
    
    def get_trading_status(self) -> Dict[str, bool]:
        """
        Check if market is currently open (simplified)
        Returns dict with trading status
        """
        now = datetime.now()
        current_time = now.time()
        
        # Simple check for VN market hours (9:00-15:00 GMT+7)
        market_open = current_time >= datetime.strptime('09:00', '%H:%M').time()
        market_close = current_time <= datetime.strptime('15:00', '%H:%M').time()
        
        is_trading = market_open and market_close and now.weekday() < 5  # Mon-Fri
        
        return {
            'is_trading': is_trading,
            'current_time': current_time,
            'market_open': '09:00',
            'market_close': '15:00'
        }
