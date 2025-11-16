"""
Support and Resistance Level Detection Module

This module uses scipy.signal.find_peaks to identify support and resistance levels
based on the approach described in the Medium article.
Returns exact price levels (not zones) for drawing lines.

Reference: https://medium.com/@itayv/support-and-resistance-levels-in-python-594a0635533e
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from scipy.signal import find_peaks


class SupportResistanceAnalyzer:
    """Analyzer for detecting support and resistance levels using peak detection"""
    
    def __init__(self):
        """Initialize the analyzer"""
        pass
    
    def find_levels(
        self,
        df: pd.DataFrame,
        current_price: Optional[float] = None,
        prominence_factor: float = 0.5,
        distance: int = 5,
        min_touches: int = 2,
        tolerance_percent: float = 1.5
    ) -> Dict[str, List[Dict]]:
        """
        Find support and resistance levels using peak detection
        
        Args:
            df: DataFrame with OHLCV data (must be sorted by timestamp)
            current_price: Current stock price (optional, for filtering)
            prominence_factor: Factor to calculate prominence (std * factor)
            distance: Minimum distance between peaks (default: 5 bars)
            min_touches: Minimum touches needed for a level to be valid
            tolerance_percent: Percentage tolerance for merging close levels
        
        Returns:
            Dictionary with:
            - resistance_levels: List of resistance levels (sorted by price desc)
            - support_levels: List of support levels (sorted by price asc)
            Each level contains:
            - price: Exact price level
            - touch_points: List of indices where price touched this level
            - touch_count: Number of touches
            - strength: 'strong' or 'weak'
            - total_volume: Total volume at this level
            - latest_touch: Timestamp of latest touch
        """
        try:
            if df.empty or len(df) < distance * 2:
                return {'resistance_levels': [], 'support_levels': []}
            
            # Get price data
            high_values = df['high'].values
            low_values = df['low'].values
            close_values = df['close'].values
            volume_values = df['volume'].values if 'volume' in df.columns else np.zeros(len(df))
            timestamps = df['timestamp'].values if 'timestamp' in df.columns else df.index
            
            # Calculate adaptive prominence based on price volatility
            price_std = np.std(close_values)
            prominence_high = price_std * prominence_factor
            prominence_low = price_std * prominence_factor
            
            # Find resistance levels (peaks in high prices)
            resistance_peaks, resistance_properties = find_peaks(
                high_values,
                prominence=prominence_high,
                distance=distance
            )
            
            # Find support levels (troughs in low prices - invert signal)
            support_troughs, support_properties = find_peaks(
                -low_values,  # Invert for minima
                prominence=prominence_low,
                distance=distance
            )
            
            # Convert peaks to resistance levels
            resistance_levels = self._process_peaks(
                resistance_peaks,
                high_values,
                volume_values,
                timestamps,
                df,
                is_resistance=True,
                min_touches=min_touches,
                tolerance_percent=tolerance_percent
            )
            
            # Convert troughs to support levels
            support_levels = self._process_peaks(
                support_troughs,
                low_values,
                volume_values,
                timestamps,
                df,
                is_resistance=False,
                min_touches=min_touches,
                tolerance_percent=tolerance_percent
            )
            
            # Filter by current price if provided
            if current_price is not None:
                resistance_levels = [l for l in resistance_levels if l['price'] > current_price]
                support_levels = [l for l in support_levels if l['price'] < current_price]
            
            # Sort resistance levels (highest first), support levels (lowest first)
            resistance_levels.sort(key=lambda x: x['price'], reverse=True)
            support_levels.sort(key=lambda x: x['price'])
            
            return {
                'resistance_levels': resistance_levels,
                'support_levels': support_levels
            }
            
        except Exception as e:
            print(f"Error finding support/resistance levels: {e}")
            import traceback
            traceback.print_exc()
            return {'resistance_levels': [], 'support_levels': []}
    
    def _process_peaks(
        self,
        peak_indices: np.ndarray,
        price_values: np.ndarray,
        volume_values: np.ndarray,
        timestamps: np.ndarray,
        df: pd.DataFrame,
        is_resistance: bool,
        min_touches: int,
        tolerance_percent: float
    ) -> List[Dict]:
        """
        Process peak indices into support/resistance levels with touch points
        
        Args:
            peak_indices: Array of peak/trough indices
            price_values: Array of price values (highs for resistance, lows for support)
            volume_values: Array of volume values
            timestamps: Array of timestamps
            df: Original DataFrame
            is_resistance: True for resistance, False for support
            min_touches: Minimum touches needed
            tolerance_percent: Tolerance for merging close levels
        
        Returns:
            List of level dictionaries
        """
        if len(peak_indices) == 0:
            return []
        
        # Create initial levels from peaks
        initial_levels = []
        for idx in peak_indices:
            initial_levels.append({
                'price': float(price_values[idx]),
                'touch_points': [int(idx)],
                'touch_count': 1,
                'total_volume': float(volume_values[idx]),
                'latest_touch': timestamps[idx] if hasattr(timestamps[idx], 'strftime') else pd.Timestamp(timestamps[idx]),
                'strength': 'weak'  # Will be updated based on touch count
            })
        
        # Merge close levels (within tolerance)
        merged_levels = self._merge_close_levels(
            initial_levels,
            tolerance_percent,
            min_touches
        )
        
        # Find additional touch points for each level
        for level in merged_levels:
            level['touch_points'] = self._find_touch_points(
                df,
                level['price'],
                is_resistance,
                tolerance_percent
            )
            level['touch_count'] = len(level['touch_points'])
            
            # Calculate total volume at all touch points
            total_vol = 0
            latest_touch = None
            for touch_idx in level['touch_points']:
                total_vol += float(volume_values[touch_idx])
                touch_ts = timestamps[touch_idx] if hasattr(timestamps[touch_idx], 'strftime') else pd.Timestamp(timestamps[touch_idx])
                if latest_touch is None or touch_ts > latest_touch:
                    latest_touch = touch_ts
            
            level['total_volume'] = total_vol
            level['latest_touch'] = latest_touch
            
            # Classify strength: strong if >= 3 touches, weak otherwise
            level['strength'] = 'strong' if level['touch_count'] >= 3 else 'weak'
        
        # Filter out levels that don't meet minimum touches
        return [l for l in merged_levels if l['touch_count'] >= min_touches]
    
    def _merge_close_levels(
        self,
        levels: List[Dict],
        tolerance_percent: float,
        min_touches: int
    ) -> List[Dict]:
        """
        Merge levels that are close together (within tolerance)
        
        Args:
            levels: List of level dictionaries
            tolerance_percent: Percentage tolerance for merging
            min_touches: Minimum touches (not used here, but kept for consistency)
        
        Returns:
            List of merged levels
        """
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x['price'], reverse=True)
        merged = []
        
        for level in sorted_levels:
            merged_into_existing = False
            
            for existing in merged:
                # Check if level is within tolerance of existing level
                tolerance = existing['price'] * tolerance_percent / 100
                price_diff = abs(level['price'] - existing['price'])
                
                if price_diff <= tolerance:
                    # Merge into existing level
                    # Use weighted average price (by touch count)
                    total_touches = existing['touch_count'] + level['touch_count']
                    existing['price'] = (
                        existing['price'] * existing['touch_count'] +
                        level['price'] * level['touch_count']
                    ) / total_touches
                    
                    # Merge touch points
                    existing['touch_points'].extend(level['touch_points'])
                    existing['touch_count'] = total_touches
                    existing['total_volume'] += level['total_volume']
                    
                    # Update latest touch if more recent
                    if level['latest_touch'] > existing['latest_touch']:
                        existing['latest_touch'] = level['latest_touch']
                    
                    merged_into_existing = True
                    break
            
            if not merged_into_existing:
                merged.append(level.copy())
        
        return merged
    
    def _find_touch_points(
        self,
        df: pd.DataFrame,
        level_price: float,
        is_resistance: bool,
        tolerance_percent: float
    ) -> List[int]:
        """
        Find all indices where price touched the level (within tolerance)
        
        Args:
            df: DataFrame with OHLCV data
            level_price: The price level to check
            is_resistance: True for resistance, False for support
            tolerance_percent: Percentage tolerance
        
        Returns:
            List of indices where price touched the level
        """
        tolerance = level_price * tolerance_percent / 100
        touch_indices = []
        
        if is_resistance:
            # For resistance, check if high touched the level
            price_column = df['high']
        else:
            # For support, check if low touched the level
            price_column = df['low']
        
        for idx in range(len(df)):
            price = price_column.iloc[idx]
            if abs(price - level_price) <= tolerance:
                touch_indices.append(idx)
        
        return touch_indices
