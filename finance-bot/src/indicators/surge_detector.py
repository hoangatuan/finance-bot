"""
Surge Detection Module
Detects volume and price surges in stock data
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

try:
    from .ta import TechnicalAnalyzer
except ImportError:
    from indicators.ta import TechnicalAnalyzer


class SurgeDetector:
    """
    Detects volume and price surges in stock data
    """
    
    def __init__(
        self,
        volume_multiplier: float = 1.5,
        price_change_pct: float = 3.0,
        lookback_periods: int = 20
    ):
        """
        Initialize surge detector
        
        Args:
            volume_multiplier: Threshold for volume surge (e.g., 1.5 = 150% of average)
            price_change_pct: Threshold for price surge percentage (e.g., 3.0 = 3%)
            lookback_periods: Number of periods to look back for comparison
        """
        self.volume_multiplier = volume_multiplier
        self.price_change_pct = price_change_pct
        self.lookback_periods = lookback_periods
        self.analyzer = TechnicalAnalyzer()
    
    async def detect_volume_surge(
        self,
        df: pd.DataFrame,
        current_volume: Optional[float] = None
    ) -> Tuple[bool, Dict]:
        """
        Detect if there's a volume surge
        
        Args:
            df: DataFrame with OHLCV data (must have 'volume' column)
            current_volume: Current volume value. If None, uses last row's volume
        
        Returns:
            Tuple of (is_surge: bool, details: dict)
            Details include:
            - current_volume: Current volume value
            - average_volume: Average volume over lookback period
            - volume_ratio: current_volume / average_volume
            - is_surge: Whether surge threshold is met
        """
        try:
            if df.empty or 'volume' not in df.columns:
                return False, {'error': 'Invalid data or missing volume column'}
            
            # Get current volume (use last row if not provided)
            if current_volume is None:
                current_volume = df['volume'].iloc[-1]
            
            # Calculate volume indicators
            volume_indicators = await self.analyzer.calculate_volume_analysis(df)
            
            # Get volume ratio (prefer 20-period, fallback to 50-period)
            volume_ratio = None
            average_volume = None
            
            if 'vol_ratio_20' in volume_indicators:
                vol_ratio_20 = volume_indicators['vol_ratio_20']
                if not vol_ratio_20.isnull().all() and len(vol_ratio_20) > 0:
                    volume_ratio = vol_ratio_20.iloc[-1]
                    if 'vol_sma20' in volume_indicators:
                        average_volume = volume_indicators['vol_sma20'].iloc[-1]
            
            # Fallback to 50-period if 20-period not available
            if volume_ratio is None or np.isnan(volume_ratio):
                if 'vol_ratio_50' in volume_indicators:
                    vol_ratio_50 = volume_indicators['vol_ratio_50']
                    if not vol_ratio_50.isnull().all() and len(vol_ratio_50) > 0:
                        volume_ratio = vol_ratio_50.iloc[-1]
                        if 'vol_sma50' in volume_indicators:
                            average_volume = volume_indicators['vol_sma50'].iloc[-1]
            
            # If still no ratio, calculate manually
            if volume_ratio is None or np.isnan(volume_ratio):
                if len(df) >= self.lookback_periods:
                    recent_volumes = df['volume'].iloc[-self.lookback_periods:]
                    average_volume = recent_volumes.mean()
                    if average_volume > 0:
                        volume_ratio = current_volume / average_volume
                    else:
                        volume_ratio = 0.0
                else:
                    # Not enough data
                    return False, {
                        'error': f'Insufficient data (need at least {self.lookback_periods} periods)',
                        'current_volume': current_volume,
                        'data_points': len(df)
                    }
            
            # Check if surge threshold is met
            is_surge = volume_ratio >= self.volume_multiplier
            
            return is_surge, {
                'current_volume': current_volume,
                'average_volume': average_volume if average_volume is not None else 0.0,
                'volume_ratio': float(volume_ratio),
                'threshold': self.volume_multiplier,
                'is_surge': is_surge
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    async def detect_price_surge(
        self,
        df: pd.DataFrame,
        periods: int = 1
    ) -> Tuple[bool, Dict]:
        """
        Detect if there's a price surge
        
        Args:
            df: DataFrame with OHLCV data (must have 'close' column)
            periods: Number of periods to look back for price change (default: 1 = compare to previous period)
        
        Returns:
            Tuple of (is_surge: bool, details: dict)
            Details include:
            - current_price: Current close price
            - previous_price: Price N periods ago
            - price_change: Absolute price change
            - price_change_pct: Percentage price change
            - is_surge: Whether surge threshold is met
        """
        try:
            if df.empty or 'close' not in df.columns:
                return False, {'error': 'Invalid data or missing close column'}
            
            if len(df) < periods + 1:
                return False, {
                    'error': f'Insufficient data (need at least {periods + 1} periods)',
                    'data_points': len(df)
                }
            
            # Get current and previous prices
            current_price = df['close'].iloc[-1]
            previous_price = df['close'].iloc[-(periods + 1)]
            
            # Calculate price change
            price_change = current_price - previous_price
            price_change_pct = (price_change / previous_price) * 100 if previous_price > 0 else 0.0
            
            # Check if surge threshold is met (absolute value for both up and down)
            is_surge = abs(price_change_pct) >= self.price_change_pct
            
            return is_surge, {
                'current_price': float(current_price),
                'previous_price': float(previous_price),
                'price_change': float(price_change),
                'price_change_pct': float(price_change_pct),
                'threshold': self.price_change_pct,
                'is_surge': is_surge,
                'direction': 'up' if price_change > 0 else 'down'
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    async def detect_surge(
        self,
        df: pd.DataFrame,
        require_both: bool = False
    ) -> Dict:
        """
        Detect both volume and price surges
        
        Args:
            df: DataFrame with OHLCV data
            require_both: If True, both volume and price must surge. If False, either one triggers
        
        Returns:
            Dictionary with:
            - has_surge: bool - Whether any surge is detected
            - volume_surge: dict - Volume surge details
            - price_surge: dict - Price surge details
            - timestamp: datetime - Detection timestamp
        """
        try:
            # Detect volume surge
            volume_is_surge, volume_details = await self.detect_volume_surge(df)
            
            # Detect price surge
            price_is_surge, price_details = await self.detect_price_surge(df)
            
            # Determine if overall surge is detected
            if require_both:
                has_surge = volume_is_surge and price_is_surge
            else:
                has_surge = volume_is_surge or price_is_surge
            
            return {
                'has_surge': has_surge,
                'volume_surge': volume_details,
                'price_surge': price_details,
                'timestamp': datetime.now(),
                'ticker': df['ticker'].iloc[-1] if 'ticker' in df.columns else None
            }
            
        except Exception as e:
            return {
                'has_surge': False,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def update_thresholds(
        self,
        volume_multiplier: Optional[float] = None,
        price_change_pct: Optional[float] = None
    ):
        """
        Update surge detection thresholds
        
        Args:
            volume_multiplier: New volume multiplier threshold
            price_change_pct: New price change percentage threshold
        """
        if volume_multiplier is not None:
            self.volume_multiplier = volume_multiplier
        if price_change_pct is not None:
            self.price_change_pct = price_change_pct

