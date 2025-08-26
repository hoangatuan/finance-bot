"""
Base fetcher class for stock data
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from datetime import datetime, date
import pandas as pd
from dataclasses import dataclass


@dataclass
class StockData:
    """Standardized stock data format"""
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    data_type: str  # 'historical' or 'realtime'
    interval: str   # '1m', '5m', '15m', '30m', '1H', '1D', '1W', '1M'


class BaseFetcher(ABC):
    """Abstract base class for all data fetchers"""
    
    def __init__(self, rate_limit: int = 60):
        self.rate_limit = rate_limit
        self.last_request_time = 0
    
    @abstractmethod
    async def fetch_historical(
        self, 
        ticker: str, 
        start_date: Union[str, date], 
        end_date: Union[str, date],
        interval: str = '1D'
    ) -> pd.DataFrame:
        """Fetch historical data for a ticker"""
        pass
    
    @abstractmethod
    async def fetch_realtime(
        self, 
        tickers: List[str]
    ) -> List[StockData]:
        """Fetch real-time data for multiple tickers"""
        pass
    
    @abstractmethod
    def normalize_data(self, raw_data: pd.DataFrame, ticker: str, data_type: str) -> pd.DataFrame:
        """Normalize raw data to standard format"""
        pass
    
    def validate_interval(self, interval: str) -> bool:
        """Validate if interval is supported"""
        valid_intervals = ['1m', '5m', '15m', '30m', '1H', '1D', '1W', '1M']
        return interval in valid_intervals
    
    def get_interval_minutes(self, interval: str) -> int:
        """Convert interval to minutes for scheduling"""
        interval_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1H': 60,
            '1D': 1440,
            '1W': 10080,
            '1M': 43200
        }
        return interval_map.get(interval, 1)
