# Support and Resistance Technical Analysis

## Overview

This module implements a comprehensive support and resistance zone detection system using pivot point analysis with confidence scoring for breakout predictions. Instead of identifying exact price levels, the system creates **zones** (price ranges) where support or resistance is likely to occur, which is more realistic as markets rarely respect exact price points.

## Core Concept

### What are Support and Resistance Zones?

- **Support Zone**: A price range where buying pressure is historically strong, preventing the price from falling further
- **Resistance Zone**: A price range where selling pressure is historically strong, preventing the price from rising further

Unlike traditional exact price levels, **zones** account for market volatility and provide more flexible and realistic price levels for trading decisions.

## How It Works

### Phase 1: Data Collection
1. **Extended Historical Data**: Fetches minimum 200+ daily candles (recommended 250 days ≈ 1 year)
2. **Current Price**: Uses real-time API (`fetch_realtime()`) to get current market price
3. **Data Validation**: Ensures data quality and proper sorting by timestamp

### Phase 2: Pivot Detection

**Pivot High (Resistance Potential)**:
- A candle where the **high** is higher than N candles before and after
- Default: N = 5 (5 bars left, 5 bars right)
- Identifies swing highs that could become resistance levels

**Pivot Low (Support Potential)**:
- A candle where the **low** is lower than N candles before and after
- Default: N = 5 (5 bars left, 5 bars right)
- Identifies swing lows that could become support levels

**Algorithm**:
```
For each candle i (from left_bars to length - right_bars):
    Check if high[i] > all highs in range [i-left_bars : i+right_bars]
    If yes → Pivot High found at high[i]
    
    Check if low[i] < all lows in range [i-left_bars : i+right_bars]
    If yes → Pivot Low found at low[i]
```

### Phase 3: Zone Creation

Pivots are grouped into zones using clustering logic:

1. **Grouping**: Pivots within tolerance (default 1.5%) are grouped together
2. **Zone Boundaries**:
   - Upper: Highest pivot price in group
   - Lower: Lowest pivot price in group
   - Middle: Average of upper and lower
3. **Zone Strength**: Calculated based on:
   - Number of touches (more pivots = stronger zone)
   - Total volume at zone level
   - Zone width (narrower = stronger)
   - Recency of touches
4. **Filtering**: Only zones with minimum touches (default: 2) are considered valid

### Phase 4: Current Price Analysis

- **Nearest Support**: Highest support zone below current price
- **Nearest Resistance**: Lowest resistance zone above current price
- **Distance Calculation**: Percentage distance from current price to zone

### Phase 5: Confidence Scoring System

When price breaks through a support/resistance zone, the system calculates a confidence score (0-1) indicating how likely the breakout is to be genuine vs. a false signal.

#### Score Components (Weighted Average):

1. **Volume Strength (25% weight)**
   - Compares current volume to 20-day, 50-day, and 200-day averages
   - Stronger volume = higher confidence in breakout
   - Scoring: Current volume > 200-day avg (+0.4), > 50-day (+0.3), > 20-day (+0.2)
   - Bonus: 1.5x any average (+0.1)

2. **Zone Strength (25% weight)**
   - Based on historical zone characteristics
   - Factors: Touch count, total volume, zone width, recency
   - Stronger historical zone = higher confidence when broken

3. **Momentum Indicators (25% weight)**
   - **RSI Analysis**:
     - For resistance breaks: RSI 50-70 is ideal (strong but not overbought)
     - For support breaks: RSI 30-50 is ideal (weak but not oversold)
   - **MACD Analysis**:
     - MACD > Signal for bullish breakouts
     - MACD < Signal for bearish breakouts
     - MACD histogram direction confirms momentum

4. **Breakout Pattern (25% weight)**
   - Price closing above/below zone: +0.5
   - Multiple consecutive closes: +0.3
   - Clean break (no retest): +0.2

#### Confidence Interpretation:
- **0.75-1.0**: Very High Confidence - Strong breakout signal
- **0.60-0.75**: High Confidence - Good breakout potential
- **0.45-0.60**: Moderate Confidence - Wait for confirmation
- **0.30-0.45**: Low Confidence - Weak signal
- **0.0-0.30**: Very Low Confidence - False breakout likely

## Technical Implementation

### Module Structure

```
src/indicators/
├── ta.py                          # Main technical analyzer
├── support_resistance.py          # SR analysis module
└── SupportAndResistantTA.md       # This documentation
```

### Key Functions

#### `SupportResistanceAnalyzer` Class

1. **`find_pivots(df, left_bars=5, right_bars=5)`**
   - Input: DataFrame with OHLCV data
   - Output: Dictionary with `pivot_highs` and `pivot_lows` lists
   - Each pivot contains: index, price, timestamp, volume

2. **`create_pivot_zones(pivots, current_price, tolerance_percent=1.5, min_touches=2)`**
   - Input: Pivot lists, current price, grouping parameters
   - Output: Dictionary with `resistance_zones`, `support_zones`, `all_zones`
   - Each zone contains: upper, lower, middle, touch_count, strength, distance_pct

3. **`calculate_breakout_confidence(zone, indicators, df, is_resistance)`**
   - Input: Zone dict, indicators dict, DataFrame, zone type
   - Output: Confidence score with detailed breakdown
   - Returns: confidence_score, breakdown, interpretation

### Data Flow

```
Historical Data (200+ days)
    ↓
Find Pivots (swing highs/lows)
    ↓
Group Pivots into Zones
    ↓
Filter by Current Price (above/below)
    ↓
Calculate Zone Strength
    ↓
For Each Zone:
    Calculate Breakout Confidence
        ↓
    Volume Analysis
        ↓
    Momentum Analysis (RSI/MACD)
        ↓
    Pattern Analysis
        ↓
    Weighted Score (0-1)
```

## Usage Example

### Basic Usage in main.py

```python
# Run the test function with default ticker (HPG)
python3 main.py --test-sr

# Or specify a different ticker
python3 main.py --test-sr VNM
```

### Programmatic Usage

```python
from indicators.support_resistance import SupportResistanceAnalyzer

# 1. Fetch extended historical data (200+ days recommended)
df = await fetch_extended_historical('HPG', days=250)

# 2. Get current price (with fallback to historical close)
current_price = await get_current_price('HPG', df.iloc[-1]['close'])

# 3. Calculate technical indicators first
processed_df = await run_technical_analysis(df)

# 4. Initialize SR analyzer and find pivots
sr_analyzer = SupportResistanceAnalyzer()
pivots = await sr_analyzer.find_pivots(
    processed_df,
    left_bars=5,   # Bars to look left
    right_bars=5   # Bars to look right
)

# 5. Create pivot zones
zones = await sr_analyzer.create_pivot_zones(
    pivots,
    current_price,
    tolerance_percent=1.5,  # Group pivots within 1.5%
    min_touches=2           # Minimum 2 pivots to form zone
)

# 6. Get latest indicators for confidence calculation
latest_indicators = processed_df.iloc[-1].to_dict()

# 7. Calculate confidence for nearest zones
if zones['resistance_zones']:
    nearest_resistance = zones['resistance_zones'][0]
    confidence = await sr_analyzer.calculate_breakout_confidence(
        nearest_resistance,
        latest_indicators,
        processed_df,
        is_resistance=True
    )
    
    print(f"Nearest Resistance: {nearest_resistance['middle']:.2f}")
    print(f"Zone Range: {nearest_resistance['lower']:.2f} - {nearest_resistance['upper']:.2f}")
    print(f"Confidence Score: {confidence['confidence_score']:.2f} / 1.00")
    print(f"Interpretation: {confidence['interpretation']}")
    print(f"Breakdown:")
    print(f"  Volume: {confidence['breakdown']['volume_strength']:.2f}")
    print(f"  Zone: {confidence['breakdown']['zone_strength']:.2f}")
    print(f"  Momentum: {confidence['breakdown']['momentum_strength']:.2f}")
    print(f"  Pattern: {confidence['breakdown']['pattern_strength']:.2f}")
```

## Parameters & Configuration

### Pivot Detection
- `left_bars`: Number of bars to look left (default: 5)
- `right_bars`: Number of bars to look right (default: 5)
- **Recommendation**: 5 works well for daily candles, adjust for other timeframes

### Zone Creation
- `tolerance_percent`: Percentage tolerance for grouping pivots (default: 1.5%)
- `min_touches`: Minimum pivots needed to form valid zone (default: 2)
- **Recommendation**: 1.5% works for most Vietnamese stocks, increase for volatile stocks

### Confidence Scoring
- Volume periods: 20, 50, 200 days
- Component weights: 25% each (adjustable based on backtesting)
- **Recommendation**: Tune weights based on historical performance

## Advantages of This Approach

1. **Zones vs. Exact Prices**: More realistic, accounts for market volatility
2. **Multi-Factor Confidence**: Considers volume, momentum, patterns, and zone strength
3. **Historical Validation**: Zones based on actual price action (pivots)
4. **Adaptive**: Can adjust parameters based on stock volatility
5. **Comprehensive**: Integrates with existing technical indicators (RSI, MACD)

## Output Interpretation

### Zone Information
- **Upper/Lower**: Price range boundaries of the zone
- **Middle**: Average price of the zone (target level)
- **Distance %**: Percentage distance from current price to zone middle
  - Positive for resistance (above current price)
  - Negative for support (below current price)
- **Strength**: Zone strength score (0-1), based on touches, volume, and width
- **Touches**: Number of pivot points forming the zone (more = stronger)

### Confidence Score Breakdown
Each component contributes to the overall confidence:
- **Volume Strength (0-1)**: How current volume compares to historical averages
- **Zone Strength (0-1)**: Historical significance of the zone
- **Momentum Strength (0-1)**: RSI and MACD alignment with breakout direction
- **Pattern Strength (0-1)**: Cleanliness of the breakout pattern

### Example Output
```
Nearest Resistance: 28.50
Zone Range: 28.00 - 29.00
Confidence Score: 0.72 / 1.00
Interpretation: High Confidence - Good breakout potential
Breakdown:
  Volume: 0.80  (Strong volume)
  Zone: 0.65    (Moderate zone strength)
  Momentum: 0.75 (Good momentum alignment)
  Pattern: 0.70 (Clean breakout pattern)
```

### Trading Signals
- **Confidence > 0.75**: Consider taking position, strong signal
- **Confidence 0.60-0.75**: Good potential, confirm with additional factors
- **Confidence 0.45-0.60**: Wait for confirmation, monitor closely
- **Confidence < 0.45**: Weak signal, avoid or use with caution

## Limitations & Considerations

1. **Lagging Indicator**: Pivots are confirmed only after bars complete
2. **Market Context**: May not account for fundamental events or news
3. **Timeframe Dependency**: Best results with daily candles, may vary on other timeframes
4. **False Breakouts**: Even with confidence scoring, false signals can occur
5. **Data Requirements**: Needs sufficient historical data (200+ days recommended)
6. **Price Unit Consistency**: VNStock API may return prices in different units; system validates and uses historical close if inconsistent

## Future Enhancements

1. **Dynamic Tolerance**: Adjust tolerance based on stock volatility (ATR-based)
2. **Volume Profile**: Add volume-at-price analysis for stronger zones
3. **Multiple Timeframes**: Combine daily, weekly, monthly zones
4. **Backtesting Framework**: Validate confidence scores against historical breakouts
5. **Machine Learning**: Train ML model on historical breakout success rates

## References

- Technical Analysis: Pivot Point Trading
- Support/Resistance Zone Theory
- Volume-Price Analysis
- Breakout Pattern Recognition

