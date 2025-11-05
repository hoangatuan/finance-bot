"""
Support and Resistance Zone Detection Module
"""
import math
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class SupportResistanceAnalyzer:
    """Analyzer for detecting support and resistance zones using pivot point analysis"""
    
    def __init__(self):
        """Initialize the analyzer"""
        pass
    
    async def find_pivots(
        self,
        df: pd.DataFrame,
        left_bars: int = 5,
        right_bars: int = 5
    ) -> Dict:
        """
        Find pivot highs and pivot lows
        
        Args:
            df: DataFrame with OHLCV data (must be sorted by timestamp)
            left_bars: Number of bars to look left
            right_bars: Number of bars to look right
        
        Returns:
            Dictionary with pivot_highs and pivot_lows
        """
        try:
            if df.empty or len(df) < (left_bars + right_bars + 1):
                return {'pivot_highs': [], 'pivot_lows': []}
            
            high = df['high'].values
            low = df['low'].values
            timestamp = df['timestamp'].values if 'timestamp' in df.columns else df.index
            
            pivot_highs = []
            pivot_lows = []
            
            for i in range(left_bars, len(df) - right_bars):
                # Check for pivot high
                is_pivot_high = True
                current_high = high[i]
                
                # Check left bars
                for j in range(i - left_bars, i):
                    if high[j] >= current_high:
                        is_pivot_high = False
                        break
                
                # Check right bars
                if is_pivot_high:
                    for j in range(i + 1, i + right_bars + 1):
                        if high[j] >= current_high:
                            is_pivot_high = False
                            break
                
                if is_pivot_high:
                    pivot_highs.append({
                        'index': i,
                        'price': float(current_high),
                        'timestamp': timestamp[i] if hasattr(timestamp[i], 'strftime') else pd.Timestamp(timestamp[i]),
                        'volume': float(df.iloc[i]['volume']) if 'volume' in df.columns else 0
                    })
                
                # Check for pivot low
                is_pivot_low = True
                current_low = low[i]
                
                # Check left bars
                for j in range(i - left_bars, i):
                    if low[j] <= current_low:
                        is_pivot_low = False
                        break
                
                # Check right bars
                if is_pivot_low:
                    for j in range(i + 1, i + right_bars + 1):
                        if low[j] <= current_low:
                            is_pivot_low = False
                            break
                
                if is_pivot_low:
                    pivot_lows.append({
                        'index': i,
                        'price': float(current_low),
                        'timestamp': timestamp[i] if hasattr(timestamp[i], 'strftime') else pd.Timestamp(timestamp[i]),
                        'volume': float(df.iloc[i]['volume']) if 'volume' in df.columns else 0
                    })
            
            return {
                'pivot_highs': pivot_highs,
                'pivot_lows': pivot_lows
            }
            
        except Exception as e:
            print(f"Error finding pivots: {e}")
            return {'pivot_highs': [], 'pivot_lows': []}
    
    def _calculate_zone_strength(self, zone: Dict) -> float:
        """
        Calculate zone strength based on multiple factors
        
        Args:
            zone: Zone dictionary with pivot information
        
        Returns:
            Strength score between 0-1
        """
        try:
            touch_score = min(zone['touch_count'] / 5.0, 1.0)  # Max at 5 touches
            
            # Volume score (normalized)
            volume_score = min(zone['total_volume'] / (zone['total_volume'] + 1000000), 1.0)
            
            # Width score (narrower is better, max 2% width = strong)
            width_score = max(0, 1.0 - (zone['width_pct'] / 2.0))
            
            # Combine with weights
            strength = (touch_score * 0.4 + volume_score * 0.3 + width_score * 0.3)
            
            return min(strength, 1.0)
        except:
            return 0.5
    
    def _find_touching_levels(
        self,
        df: pd.DataFrame,
        use_highs: bool = True,
        tolerance_percent: float = 1.5,
        min_touches: int = 3
    ) -> List[Dict]:
        """
        Find price levels where multiple candles touched (for consolidation zones)
        This complements pivot detection by catching zones where price bounces
        multiple times at similar levels without strict pivots.
        
        Args:
            df: DataFrame with OHLCV data
            use_highs: True for resistance (use highs), False for support (use lows)
            tolerance_percent: Percentage tolerance for grouping touches
            min_touches: Minimum touches needed to form a zone
        
        Returns:
            List of zone dictionaries
        """
        try:
            if df.empty:
                return []
            
            # Use highs for resistance, lows for support
            price_column = 'high' if use_highs else 'low'
            prices = df[price_column].values
            volumes = df['volume'].values if 'volume' in df.columns else [0] * len(df)
            timestamps = df['timestamp'].values if 'timestamp' in df.columns else df.index
            
            # Create list of all touches
            touches = []
            for i in range(len(df)):
                touches.append({
                    'price': float(prices[i]),
                    'volume': float(volumes[i]),
                    'timestamp': timestamps[i] if hasattr(timestamps[i], 'strftime') else pd.Timestamp(timestamps[i]),
                    'index': i
                })
            
            # Sort by price (descending for resistance, ascending for support)
            touches.sort(key=lambda x: x['price'], reverse=use_highs)
            
            # Group touches into zones
            zones = []
            current_zone = None
            
            for touch in touches:
                if current_zone is None:
                    current_zone = {
                        'pivots': [touch],
                        'upper': touch['price'],
                        'lower': touch['price'],
                        'middle': touch['price'],
                        'total_volume': touch['volume'],
                        'touch_count': 1,
                        'latest_touch': touch['timestamp']
                    }
                else:
                    # Check if touch fits in current zone
                    tolerance = current_zone['middle'] * tolerance_percent / 100
                    price_diff = abs(touch['price'] - current_zone['middle'])
                    
                    if price_diff <= tolerance:
                        # Add to current zone
                        current_zone['pivots'].append(touch)
                        current_zone['upper'] = max(current_zone['upper'], touch['price'])
                        current_zone['lower'] = min(current_zone['lower'], touch['price'])
                        current_zone['middle'] = (current_zone['upper'] + current_zone['lower']) / 2
                        current_zone['total_volume'] += touch['volume']
                        current_zone['touch_count'] += 1
                        
                        # Update latest touch if more recent
                        if isinstance(touch['timestamp'], pd.Timestamp) and isinstance(current_zone['latest_touch'], pd.Timestamp):
                            if touch['timestamp'] > current_zone['latest_touch']:
                                current_zone['latest_touch'] = touch['timestamp']
                    else:
                        # Save current zone if it meets minimum touches
                        if current_zone['touch_count'] >= min_touches:
                            zones.append(current_zone)
                        
                        # Start new zone
                        current_zone = {
                            'pivots': [touch],
                            'upper': touch['price'],
                            'lower': touch['price'],
                            'middle': touch['price'],
                            'total_volume': touch['volume'],
                            'touch_count': 1,
                            'latest_touch': touch['timestamp']
                        }
            
            # Don't forget the last zone
            if current_zone and current_zone['touch_count'] >= min_touches:
                zones.append(current_zone)
            
            return zones
            
        except Exception as e:
            print(f"Error finding touching levels: {e}")
            return []
    
    async def create_pivot_zones(
        self,
        pivots: Dict,
        current_price: float,
        df: pd.DataFrame = None,
        tolerance_percent: float = 1.5,
        min_touches: int = 2,
        include_touching_levels: bool = True
    ) -> Dict:
        """
        Group pivots into zones, optionally including touching levels detection
        
        Args:
            pivots: Dictionary with 'pivot_highs' and 'pivot_lows' lists
            current_price: Current stock price
            df: DataFrame with OHLCV data (required if include_touching_levels=True)
            tolerance_percent: Percentage tolerance for grouping (default 1.5%)
            min_touches: Minimum pivots needed to form a zone
            include_touching_levels: If True, also detect zones from touching levels
        
        Returns:
            Dictionary with resistance_zones, support_zones, and all_zones
        """
        try:
            all_zones = []
            
            # Process resistance zones (from pivot highs)
            resistance_zones = self._group_pivots_into_zones(
                pivots.get('pivot_highs', []),
                current_price,
                tolerance_percent,
                min_touches,
                is_resistance=True
            )
            
            # Process support zones (from pivot lows)
            support_zones = self._group_pivots_into_zones(
                pivots.get('pivot_lows', []),
                current_price,
                tolerance_percent,
                min_touches,
                is_resistance=False
            )
            
            all_zones = resistance_zones + support_zones
            
            # Additionally detect zones from touching levels (for consolidation zones)
            if include_touching_levels and df is not None and not df.empty:
                # Find touching levels for resistance (use higher min_touches to avoid noise)
                touching_resistance = self._find_touching_levels(
                    df, use_highs=True, tolerance_percent=tolerance_percent, min_touches=max(min_touches + 1, 3)
                )
                
                # Find touching levels for support
                touching_support = self._find_touching_levels(
                    df, use_highs=False, tolerance_percent=tolerance_percent, min_touches=max(min_touches + 1, 3)
                )
                
                # Merge with existing zones (avoid duplicates)
                for zone in touching_resistance:
                    # Check if this zone overlaps with existing zones
                    overlap = False
                    for existing in resistance_zones:
                        if (zone['lower'] <= existing['upper'] and zone['upper'] >= existing['lower']):
                            overlap = True
                            # Merge into existing zone if touching level has more touches or significant volume
                            if zone['touch_count'] >= existing['touch_count']:
                                # Update zone boundaries
                                existing['upper'] = max(existing['upper'], zone['upper'])
                                existing['lower'] = min(existing['lower'], zone['lower'])
                                existing['middle'] = (existing['upper'] + existing['lower']) / 2
                                existing['touch_count'] = max(existing['touch_count'], zone['touch_count'])
                                existing['total_volume'] += zone['total_volume']
                                existing['pivots'].extend(zone['pivots'])
                            break
                    
                    if not overlap:
                        resistance_zones.append(zone)
                
                for zone in touching_support:
                    # Check if this zone overlaps with existing zones
                    overlap = False
                    for existing in support_zones:
                        if (zone['lower'] <= existing['upper'] and zone['upper'] >= existing['lower']):
                            overlap = True
                            # Merge into existing zone if touching level has more touches or significant volume
                            if zone['touch_count'] >= existing['touch_count']:
                                # Update zone boundaries
                                existing['upper'] = max(existing['upper'], zone['upper'])
                                existing['lower'] = min(existing['lower'], zone['lower'])
                                existing['middle'] = (existing['upper'] + existing['lower']) / 2
                                existing['touch_count'] = max(existing['touch_count'], zone['touch_count'])
                                existing['total_volume'] += zone['total_volume']
                                existing['pivots'].extend(zone['pivots'])
                            break
                    
                    if not overlap:
                        support_zones.append(zone)
                
                all_zones = resistance_zones + support_zones
            
            # Calculate zone strength and distance
            for zone in all_zones:
                zone['strength'] = self._calculate_zone_strength(zone)
                zone['distance_pct'] = ((zone['middle'] - current_price) / current_price) * 100
                zone['width_pct'] = ((zone['upper'] - zone['lower']) / zone['middle']) * 100
            
            # Separate resistance and support, filter by current price
            resistance_zones = [z for z in resistance_zones if z['middle'] > current_price]
            support_zones = [z for z in support_zones if z['middle'] < current_price]
            
            # Sort by distance (nearest first)
            resistance_zones.sort(key=lambda x: x['distance_pct'])
            support_zones.sort(key=lambda x: x['distance_pct'], reverse=True)
            
            return {
                'resistance_zones': resistance_zones[:5],  # Top 5 nearest
                'support_zones': support_zones[:5],        # Top 5 nearest
                'all_zones': all_zones
            }
            
        except Exception as e:
            print(f"Error creating pivot zones: {e}")
            return {
                'resistance_zones': [],
                'support_zones': [],
                'all_zones': []
            }
    
    def _group_pivots_into_zones(
        self,
        pivots: List[Dict],
        current_price: float,
        tolerance_percent: float,
        min_touches: int,
        is_resistance: bool
    ) -> List[Dict]:
        """Group pivots into zones using clustering approach"""
        if not pivots:
            return []
        
        # Sort pivots by price (descending for resistance, ascending for support)
        sorted_pivots = sorted(pivots, key=lambda x: x['price'], reverse=is_resistance)
        
        zones = []
        current_zone = None
        
        for pivot in sorted_pivots:
            if current_zone is None:
                # Start new zone
                current_zone = {
                    'pivots': [pivot],
                    'upper': pivot['price'],
                    'lower': pivot['price'],
                    'middle': pivot['price'],
                    'total_volume': pivot.get('volume', 0),
                    'touch_count': 1,
                    'latest_touch': pivot['timestamp']
                }
            else:
                # Check if pivot fits in current zone
                tolerance = current_zone['middle'] * tolerance_percent / 100
                price_diff = abs(pivot['price'] - current_zone['middle'])
                
                if price_diff <= tolerance:
                    # Add to current zone
                    current_zone['pivots'].append(pivot)
                    current_zone['upper'] = max(current_zone['upper'], pivot['price'])
                    current_zone['lower'] = min(current_zone['lower'], pivot['price'])
                    current_zone['middle'] = (current_zone['upper'] + current_zone['lower']) / 2
                    current_zone['total_volume'] += pivot.get('volume', 0)
                    current_zone['touch_count'] += 1
                    
                    # Update latest touch if this is more recent
                    if isinstance(pivot['timestamp'], pd.Timestamp) and isinstance(current_zone['latest_touch'], pd.Timestamp):
                        if pivot['timestamp'] > current_zone['latest_touch']:
                            current_zone['latest_touch'] = pivot['timestamp']
                else:
                    # Save current zone if it meets minimum touches
                    if current_zone['touch_count'] >= min_touches:
                        zones.append(current_zone)
                    
                    # Start new zone
                    current_zone = {
                        'pivots': [pivot],
                        'upper': pivot['price'],
                        'lower': pivot['price'],
                        'middle': pivot['price'],
                        'total_volume': pivot.get('volume', 0),
                        'touch_count': 1,
                        'latest_touch': pivot['timestamp']
                    }
        
        # Don't forget the last zone
        if current_zone and current_zone['touch_count'] >= min_touches:
            zones.append(current_zone)
        
        return zones
    
    def _calculate_volume_strength(
        self,
        current_volume: float,
        volume_avg_20: float,
        volume_avg_50: float,
        volume_avg_200: float
    ) -> float:
        """Calculate volume strength score (0–1) with smooth scaling"""
        avgs = [v for v in (volume_avg_20, volume_avg_50, volume_avg_200) if v > 0]
        if not avgs or current_volume <= 0:
            return 0.0

        ratios = [current_volume / v for v in avgs]
        base_score = min(sum(min(r, 2.0) for r in ratios) / len(ratios) / 2, 1.0)

        # Extra bonus for explosive volume
        max_avg = max(avgs)
        ratio = current_volume / max_avg
        bonus = min(0.1 * math.log(ratio, 1.5), 0.2) if ratio > 1 else 0

        return min(base_score + bonus, 1.0)
    
    def _calculate_momentum_strength(
        self,
        rsi: float,
        macd: float,
        macd_signal: float,
        is_resistance_break: bool
    ) -> float:
        """Calculate momentum strength score (0-1)"""
        score = 0.0
        
        if is_resistance_break:
            # Bullish breakout
            if 50 <= rsi <= 70:
                score += 0.3
            elif rsi > 70:
                score += 0.1  # Overbought, weaker
            
            if macd > macd_signal:
                score += 0.3
            
            if (macd - macd_signal) > 0:
                score += 0.2
        else:
            # Bearish breakdown
            if 30 <= rsi <= 50:
                score += 0.3
            elif rsi < 30:
                score += 0.1  # Oversold, weaker
            
            if macd < macd_signal:
                score += 0.3
            
            if (macd - macd_signal) < 0:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_breakout_pattern(
        self,
        current_price: float,
        zone_middle: float,
        zone_upper: float,
        zone_lower: float,
        recent_highs: List[float],
        recent_lows: List[float]
    ) -> float:
        """Calculate breakout pattern strength (0-1)"""
        score = 0.0
        
        # Check if price has broken the zone
        is_resistance = current_price > zone_middle
        is_support = current_price < zone_middle
        
        if is_resistance:
            # Breaking resistance upward
            if current_price > zone_upper:
                score += 0.5
            
            # Check recent closes above zone
            closes_above = sum(1 for p in recent_highs if p > zone_upper)
            if closes_above >= 2:
                score += 0.3
            
            # Clean break (no recent retest below zone)
            if not any(p < zone_lower for p in recent_lows[-3:] if len(recent_lows) >= 3):
                score += 0.2
        
        elif is_support:
            # Breaking support downward
            if current_price < zone_lower:
                score += 0.5
            
            # Check recent closes below zone
            closes_below = sum(1 for p in recent_lows if p < zone_lower)
            if closes_below >= 2:
                score += 0.3
            
            # Clean break
            if not any(p > zone_upper for p in recent_highs[-3:] if len(recent_highs) >= 3):
                score += 0.2
        
        return min(score, 1.0)
    
    async def calculate_breakout_confidence(
        self,
        zone: Dict,
        indicators: Dict,
        df: pd.DataFrame,
        is_resistance: bool
    ) -> Dict:
        """
        Calculate overall confidence score for breakout
        
        Args:
            zone: Zone dictionary with pivot information
            indicators: Dictionary with RSI, MACD, etc.
            df: Historical DataFrame
            is_resistance: True if zone is resistance, False if support
        
        Returns:
            Dictionary with confidence score and breakdown
        """
        try:
            # Get volume averages
            if len(df) >= 200:
                volume_200 = df['volume'].tail(200).mean()
            elif len(df) >= 50:
                volume_200 = df['volume'].mean()
            else:
                volume_200 = df['volume'].mean()
            
            volume_50 = df['volume'].tail(min(50, len(df))).mean()
            volume_20 = df['volume'].tail(min(20, len(df))).mean()
            current_volume = df.iloc[-1]['volume'] if 'volume' in df.columns else 0
            
            # Calculate component scores
            volume_score = self._calculate_volume_strength(
                current_volume, volume_20, volume_50, volume_200
            )
            
            zone_score = zone.get('strength', 0.5)
            
            rsi = indicators.get('rsi_14', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            
            momentum_score = self._calculate_momentum_strength(
                rsi, macd, macd_signal, is_resistance
            )
            
            recent_highs = df['high'].tail(10).tolist()
            recent_lows = df['low'].tail(10).tolist()
            
            pattern_score = self._calculate_breakout_pattern(
                df.iloc[-1]['close'],
                zone['middle'],
                zone['upper'],
                zone['lower'],
                recent_highs,
                recent_lows
            )
            
            # Weighted average
            weights = {
                'volume': 0.25,
                'zone': 0.25,
                'momentum': 0.25,
                'pattern': 0.25
            }
            
            confidence = (
                volume_score * weights['volume'] +
                zone_score * weights['zone'] +
                momentum_score * weights['momentum'] +
                pattern_score * weights['pattern']
            )
            
            return {
                'confidence_score': confidence,
                'breakdown': {
                    'volume_strength': volume_score,
                    'zone_strength': zone_score,
                    'momentum_strength': momentum_score,
                    'pattern_strength': pattern_score
                },
                'interpretation': self._get_confidence_interpretation(confidence)
            }
            
        except Exception as e:
            print(f"Error calculating breakout confidence: {e}")
            return {
                'confidence_score': 0.0,
                'breakdown': {},
                'interpretation': 'Error calculating confidence'
            }
    
    def _get_confidence_interpretation(self, score: float) -> str:
        """Interpret confidence score"""
        if score >= 0.75:
            return "Very High Confidence - Strong breakout signal"
        elif score >= 0.60:
            return "High Confidence - Good breakout potential"
        elif score >= 0.45:
            return "Moderate Confidence - Wait for confirmation"
        elif score >= 0.30:
            return "Low Confidence - Weak signal"
        else:
            return "Very Low Confidence - False breakout likely"

