"""
Indicator Pipeline for processing raw data to indicators
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import asyncio
from datetime import datetime

from .ta import TechnicalAnalyzer


class IndicatorPipeline:
    """
    Pipeline for processing raw data to indicators
    Main purposes:
    1. Data validation and cleaning
    2. Coordinate indicator calculations
    3. Handle missing data and edge cases
    4. Normalize output format
    5. Provide batch processing for multiple tickers
    """
    
    def __init__(self, analyzer: Optional[TechnicalAnalyzer] = None):
        """
        Initialize pipeline
        
        Args:
            analyzer: TechnicalAnalyzer instance. If None, creates new one.
        """
        self.analyzer = analyzer if analyzer else TechnicalAnalyzer()
        
    async def process_historical_data(
        self, 
        df: pd.DataFrame, 
        ticker: str,
        **indicator_params
    ) -> pd.DataFrame:
        """
        Process historical data through pipeline with custom parameters
        
        Args:
            df: Raw OHLCV data
            ticker: Stock symbol
            **indicator_params: Custom parameters for indicators
            
        Returns:
            DataFrame with original data + calculated indicators
        """
        try:
            # Validate input data
            is_valid, errors = self.analyzer.validate_data_quality(df)
            if not is_valid:
                print(f"Data validation failed for {ticker}: {errors}")
                return pd.DataFrame()
            
            # Clean data
            cleaned_df = self.handle_missing_data(df.copy())
            
            # Calculate indicators
            indicators = await self.analyzer.calculate_all_indicators(
                cleaned_df, ticker, **indicator_params
            )
            
            # Remove metadata from indicators for DataFrame
            metadata = indicators.pop('metadata', {})
            
            # Convert indicators to DataFrame
            indicators_df = pd.DataFrame(indicators, index=cleaned_df.index)
            
            # Combine original data with indicators
            result_df = pd.concat([cleaned_df, indicators_df], axis=1)
            
            # Add processing metadata
            result_df['processed_at'] = datetime.now()
            result_df['ticker'] = ticker
            
            return result_df
            
        except Exception as e:
            print(f"Error processing historical data for {ticker}: {e}")
            raise
    
    async def process_realtime_data(
        self, 
        realtime_data: List, 
        historical_df: pd.DataFrame,
        **indicator_params
    ) -> pd.DataFrame:
        """
        Process real-time data with historical context
        
        Args:
            realtime_data: List of real-time data objects
            historical_df: Historical data for context
            **indicator_params: Custom parameters for indicators
            
        Returns:
            DataFrame with real-time data + indicators
        """
        try:
            if not realtime_data:
                return pd.DataFrame()
            
            # Convert real-time data to DataFrame
            realtime_df = self._convert_realtime_to_dataframe(realtime_data)
            
            # Combine with historical data for context
            combined_df = pd.concat([historical_df, realtime_df], ignore_index=True)
            
            # Remove duplicates based on timestamp
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Sort by timestamp
            combined_df = combined_df.sort_values('timestamp')
            
            # Process combined data
            result_df = await self.process_historical_data(
                combined_df, 
                realtime_data[0].get('ticker', 'UNKNOWN'), 
                **indicator_params
            )
            
            # Filter to only real-time data
            realtime_timestamps = [data.get('timestamp') for data in realtime_data]
            result_df = result_df[result_df['timestamp'].isin(realtime_timestamps)]
            
            return result_df
            
        except Exception as e:
            print(f"Error processing real-time data: {e}")
            raise
    
    def _convert_realtime_to_dataframe(self, realtime_data: List) -> pd.DataFrame:
        """
        Convert real-time data to DataFrame
        
        Args:
            realtime_data: List of real-time data objects
            
        Returns:
            DataFrame with real-time data
        """
        data_list = []
        
        for data in realtime_data:
            if isinstance(data, dict):
                row = {
                    'timestamp': data.get('timestamp'),
                    'open': data.get('open', 0),
                    'high': data.get('high', 0),
                    'low': data.get('low', 0),
                    'close': data.get('close', 0),
                    'volume': data.get('volume', 0),
                    'source': data.get('source', 'unknown'),
                    'data_type': data.get('data_type', 'realtime'),
                    'interval': data.get('interval', '1m')
                }
            else:
                # Handle object attributes
                row = {
                    'timestamp': getattr(data, 'timestamp', None),
                    'open': getattr(data, 'open', 0),
                    'high': getattr(data, 'high', 0),
                    'low': getattr(data, 'low', 0),
                    'close': getattr(data, 'close', 0),
                    'volume': getattr(data, 'volume', 0),
                    'source': getattr(data, 'source', 'unknown'),
                    'data_type': getattr(data, 'data_type', 'realtime'),
                    'interval': getattr(data, 'interval', '1m')
                }
            data_list.append(row)
        
        return pd.DataFrame(data_list)
    
    async def process_multiple_tickers(
        self, 
        tickers_data: Dict[str, pd.DataFrame],
        **indicator_params
    ) -> Dict[str, pd.DataFrame]:
        """
        Process multiple tickers with same parameters
        
        Args:
            tickers_data: Dictionary of {ticker: dataframe}
            **indicator_params: Custom parameters for indicators
            
        Returns:
            Dictionary of {ticker: processed_dataframe}
        """
        try:
            results = {}
            
            # Process each ticker
            for ticker, df in tickers_data.items():
                try:
                    processed_df = await self.process_historical_data(
                        df, ticker, **indicator_params
                    )
                    results[ticker] = processed_df
                except Exception as e:
                    print(f"Error processing {ticker}: {e}")
                    results[ticker] = pd.DataFrame()  # Empty DataFrame for failed tickers
            
            return results
            
        except Exception as e:
            print(f"Error in batch processing: {e}")
            raise
    
    def handle_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing data points
        
        Args:
            df: DataFrame with potential missing data
            
        Returns:
            Cleaned DataFrame
        """
        try:
            cleaned_df = df.copy()
            
            # Forward fill for price columns (reasonable for short gaps)
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].ffill()
            
            # For volume, fill with 0 (no trading)
            if 'volume' in cleaned_df.columns:
                cleaned_df['volume'] = cleaned_df['volume'].fillna(0)
            
            # Remove rows that still have missing values in critical columns
            critical_cols = ['open', 'high', 'low', 'close']
            cleaned_df = cleaned_df.dropna(subset=critical_cols)
            
            return cleaned_df
            
        except Exception as e:
            print(f"Error handling missing data: {e}")
            return df
    
    def validate_processed_data(self, df: pd.DataFrame, expected_indicators: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate processed data quality
        
        Args:
            df: Processed DataFrame
            expected_indicators: List of expected indicator columns
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("Processed DataFrame is empty")
            return False, errors
        
        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'ticker', 'processed_at']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Check for expected indicators
        missing_indicators = [ind for ind in expected_indicators if ind not in df.columns]
        if missing_indicators:
            errors.append(f"Missing expected indicators: {missing_indicators}")
        
        # Check for infinite values in indicators
        indicator_cols = [col for col in df.columns if col not in required_cols and col != 'timestamp']
        for col in indicator_cols:
            if col in df.columns:
                inf_count = np.isinf(df[col]).sum()
                if inf_count > 0:
                    errors.append(f"Column {col} has {inf_count} infinite values")
        
        return len(errors) == 0, errors
    
    def get_indicators_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for indicators
        
        Args:
            df: Processed DataFrame with indicators
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            summary = {}
            
            # Get indicator columns (exclude OHLCV and metadata)
            exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'ticker', 'processed_at', 'timestamp', 'source', 'data_type', 'interval']
            indicator_cols = [col for col in df.columns if col not in exclude_cols]
            
            for col in indicator_cols:
                if col in df.columns and df[col].dtype in ['float64', 'int64']:
                    series = df[col].dropna()
                    if not series.empty:
                        summary[col] = {
                            'count': len(series),
                            'mean': series.mean(),
                            'std': series.std(),
                            'min': series.min(),
                            'max': series.max(),
                            'last_value': series.iloc[-1] if len(series) > 0 else None
                        }
            
            return summary
            
        except Exception as e:
            print(f"Error generating indicators summary: {e}")
            return {}
