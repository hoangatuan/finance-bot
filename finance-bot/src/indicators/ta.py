"""
Technical Analysis module for stock indicators
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import asyncio


class TechnicalAnalyzer:
    """Main class for technical analysis with configurable parameters"""
    
    def __init__(self):
        """Initialize technical analyzer"""
        pass
        
    async def calculate_all_indicators(
        self, 
        df: pd.DataFrame, 
        ticker: str,
        sma_periods: List[int] = [20, 50],
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_avg_period: int = 20
    ) -> Dict:
        """
        Calculate all indicators with custom parameters
        
        Args:
            df: DataFrame with OHLCV data
            ticker: Stock symbol
            sma_periods: List of periods for SMA calculation
            rsi_period: Period for RSI calculation
            macd_fast: Fast period for MACD
            macd_slow: Slow period for MACD
            macd_signal: Signal period for MACD
            volume_avg_period: Period for volume average calculation
            
        Returns:
            Dictionary containing all calculated indicators
        """
        try:
            # Validate input data
            if df.empty:
                raise ValueError(f"Empty dataframe for ticker {ticker}")
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Calculate indicators
            indicators = {}
            
            # SMA calculations
            if sma_periods:
                sma_data = await self.calculate_sma(df['close'], sma_periods)
                indicators.update(sma_data)
            
            # RSI calculation
            if rsi_period:
                rsi_data = await self.calculate_rsi(df['close'], rsi_period)
                indicators[f'rsi_{rsi_period}'] = rsi_data
            
            # MACD calculation
            if macd_fast and macd_slow and macd_signal:
                macd_data = await self.calculate_macd(df['close'], macd_fast, macd_slow, macd_signal)
                indicators.update(macd_data)
            
            # Volume analysis
            if volume_avg_period:
                volume_data = await self.calculate_volume_analysis(df, volume_avg_period)
                indicators.update(volume_data)
            
            # Add metadata
            indicators['metadata'] = {
                'ticker': ticker,
                'calculated_at': pd.Timestamp.now(),
                'parameters_used': {
                    'sma_periods': sma_periods,
                    'rsi_period': rsi_period,
                    'macd_fast': macd_fast,
                    'macd_slow': macd_slow,
                    'macd_signal': macd_signal,
                    'volume_avg_period': volume_avg_period
                }
            }
            
            return indicators
            
        except Exception as e:
            print(f"Error calculating indicators for {ticker}: {e}")
            raise
    
    async def calculate_sma(self, prices: pd.Series, periods: List[int]) -> Dict[str, pd.Series]:
        """
        Calculate Simple Moving Averages
        
        Args:
            prices: Series of closing prices
            periods: List of periods for SMA calculation
            
        Returns:
            Dictionary with SMA series for each period
        """
        try:
            sma_dict = {}
            
            for period in periods:
                if period > 0 and period <= len(prices):
                    sma = prices.rolling(window=period, min_periods=period).mean()
                    sma_dict[f'sma_{period}'] = sma
                else:
                    print(f"Warning: Invalid period {period} for SMA calculation")
            
            return sma_dict
            
        except Exception as e:
            print(f"Error calculating SMA: {e}")
            raise
    
    async def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index using pandas built-in functions
        
        Args:
            prices: Series of closing prices
            period: Period for RSI calculation
            
        Returns:
            RSI series
        """
        try:
            if period <= 0 or period >= len(prices):
                raise ValueError(f"Invalid RSI period: {period}")
            
            # Calculate price changes
            delta = prices.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period, min_periods=period).mean()
            avg_losses = losses.rolling(window=period, min_periods=period).mean()
            
            # Calculate RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            # Validate output
            if rsi.isnull().all():
                raise ValueError(f"RSI calculation failed for period {period}")
            
            return rsi
            
        except Exception as e:
            print(f"Error calculating RSI: {e}")
            raise
    
    async def calculate_macd(
        self, 
        prices: pd.Series, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD, Signal, and Histogram using pandas built-in functions
        
        Args:
            prices: Series of closing prices
            fast: Fast period for MACD
            slow: Slow period for MACD
            signal: Signal period for MACD
            
        Returns:
            Dictionary with MACD, Signal, and Histogram series
        """
        try:
            if fast <= 0 or slow <= 0 or signal <= 0:
                raise ValueError(f"Invalid MACD parameters: fast={fast}, slow={slow}, signal={signal}")
            
            if fast >= slow:
                raise ValueError(f"Fast period ({fast}) must be less than slow period ({slow})")
            
            # Calculate EMAs
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate Signal line (EMA of MACD)
            macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
            
            # Calculate Histogram
            macd_histogram = macd_line - macd_signal
            
            macd_dict = {
                'macd': macd_line,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram
            }
            
            # Validate outputs
            for key, series in macd_dict.items():
                if series.isnull().all():
                    print(f"Warning: {key} contains only NaN values")
            
            return macd_dict
            
        except Exception as e:
            print(f"Error calculating MACD: {e}")
            raise
    
    async def calculate_volume_analysis(
        self, 
        df: pd.DataFrame, 
        avg_period: int = 20
    ) -> Dict[str, pd.Series]:
        """
        Calculate volume-based indicators
        
        Args:
            df: DataFrame with OHLCV data
            avg_period: Period for volume average calculation
            
        Returns:
            Dictionary with volume indicators
        """
        try:
            if 'volume' not in df.columns:
                raise ValueError("Volume column not found in dataframe")
            
            volume = df['volume']
            close = df['close']
            
            volume_dict = {}
            
            # Volume moving average
            if avg_period > 0 and avg_period <= len(volume):
                volume_dict['volume_sma'] = volume.rolling(window=avg_period, min_periods=avg_period).mean()
            else:
                volume_dict['volume_sma'] = pd.Series(index=volume.index, dtype=float)
            
            # Volume ratio (current volume / average volume)
            if 'volume_sma' in volume_dict and not volume_dict['volume_sma'].isnull().all():
                volume_sma_series = volume_dict['volume_sma']
                if isinstance(volume_sma_series, pd.Series):
                    volume_dict['volume_ratio'] = volume / volume_sma_series
                else:
                    volume_dict['volume_ratio'] = pd.Series(index=volume.index, dtype=float)
            else:
                volume_dict['volume_ratio'] = pd.Series(index=volume.index, dtype=float)
            
            # Volume change percentage
            volume_dict['volume_change_pct'] = volume.pct_change() * 100
            
            # Price-volume trend (PVT) - Fixed calculation
            price_change_pct = close.pct_change()
            pvt = (price_change_pct * volume).cumsum()
            volume_dict['pvt'] = pvt
            
            # On-balance volume (OBV)
            price_diff = close.diff()
            obv = (np.sign(price_diff) * volume).cumsum()
            volume_dict['obv'] = obv
            
            return volume_dict
            
        except Exception as e:
            print(f"Error calculating volume analysis: {e}")
            raise
    
    def validate_data_quality(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate data quality before processing
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Check for empty dataframe
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors
        
        # Check data types
        for col in required_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    errors.append(f"Column {col} is not numeric")
        
        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                if (df[col] < 0).any():
                    errors.append(f"Column {col} contains negative values")
        
        # Check for missing values
        for col in required_cols:
            if col in df.columns:
                missing_count = df[col].isnull().sum()
                if missing_count > 0:
                    errors.append(f"Column {col} has {missing_count} missing values")
        
        # Check for outliers (basic check) - Less strict
        for col in price_cols:
            if col in df.columns:
                q99 = df[col].quantile(0.99)
                q01 = df[col].quantile(0.01)
                outlier_count = ((df[col] > q99 * 1.5) | (df[col] < q01 * 0.5)).sum()
                if outlier_count > 0:
                    errors.append(f"Column {col} has {outlier_count} potential outliers")
        
        return len(errors) == 0, errors
