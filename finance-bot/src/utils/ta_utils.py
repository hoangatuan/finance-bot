"""
Technical Analysis utilities
"""
import pandas as pd
from typing import Optional, Dict

try:
    from ..indicators.ta import TechnicalAnalyzer
    from ..indicators.pipeline import IndicatorPipeline
    from ..indicators.support_resistance import SupportResistanceAnalyzer
    from .data_fetcher import get_current_price
except ImportError:
    # Fallback for when running as script
    from indicators.ta import TechnicalAnalyzer
    from indicators.pipeline import IndicatorPipeline
    from indicators.support_resistance import SupportResistanceAnalyzer
    from utils.data_fetcher import get_current_price


async def run_technical_analysis(df: pd.DataFrame, ticker: Optional[str] = None):
    """
    Run technical analysis on the fetched data
    
    Args:
        df: DataFrame with historical data
        ticker: Stock symbol (auto-detected from df if not provided)
    
    Returns:
        DataFrame with original data plus calculated technical indicators, or None if error
    """
    # Auto-detect ticker from DataFrame if not provided
    if ticker is None:
        if 'ticker' in df.columns:
            ticker = df.iloc[0]['ticker']
        else:
            ticker = 'UNKNOWN'
    
    print(f"\n🔬 Running Technical Analysis for {ticker}...")
    
    try:
        # Create technical analyzer and pipeline
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        # Process the data with technical indicators
        processed_df = await pipeline.process_historical_data(
            df, ticker,
            sma_periods=[20, 50],  # 20-day and 50-day SMA
            rsi_period=14,         # 14-day RSI
            macd_fast=12,          # MACD fast period
            macd_slow=26,          # MACD slow period
            macd_signal=9,         # MACD signal period
            volume_avg_period=20   # 20-day volume average
        )
        
        if processed_df.empty:
            print("❌ Technical analysis failed - no processed data")
            return None
        
        print(f"✅ Technical analysis completed: {len(processed_df)} records processed")
        
        # Get the latest indicators
        latest_indicators = processed_df.iloc[-1]
        
        print(f"\n📊 Latest Technical Indicators for {ticker}:")
        print(f"   SMA(20): {latest_indicators.get('sma_20', 'N/A'):,.2f}" if pd.notna(latest_indicators.get('sma_20')) else "   SMA(20): N/A")
        print(f"   SMA(50): {latest_indicators.get('sma_50', 'N/A'):,.2f}" if pd.notna(latest_indicators.get('sma_50')) else "   SMA(50): N/A")
        print(f"   RSI(14): {latest_indicators.get('rsi_14', 'N/A'):.2f}" if pd.notna(latest_indicators.get('rsi_14')) else "   RSI(14): N/A")
        print(f"   MACD: {latest_indicators.get('macd', 'N/A'):.2f}" if pd.notna(latest_indicators.get('macd')) else "   MACD: N/A")
        print(f"   MACD Signal: {latest_indicators.get('macd_signal', 'N/A'):.2f}" if pd.notna(latest_indicators.get('macd_signal')) else "   MACD Signal: N/A")
        print(f"   Volume Ratio: {latest_indicators.get('volume_ratio', 'N/A'):.2f}" if pd.notna(latest_indicators.get('volume_ratio')) else "   Volume Ratio: N/A")
        
        # Get indicators summary
        summary = pipeline.get_indicators_summary(processed_df)
        print(f"\n📈 Indicators Summary:")
        for indicator, stats in summary.items():
            if stats['last_value'] is not None:
                print(f"   {indicator}: mean={stats['mean']:.2f}, last={stats['last_value']:.2f}")
        
        return processed_df
        
    except Exception as e:
        print(f"❌ Error in technical analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


async def analyze_support_resistance(ticker: str, df: pd.DataFrame, indicators: Dict):
    """
    Analyze support and resistance zones - simple call to get data
    
    Args:
        ticker: Stock symbol
        df: DataFrame with historical data and indicators
        indicators: Dictionary with latest indicator values
    
    Returns:
        Dictionary with resistance_zones, support_zones, current_price, and ticker
    """
    # Get current price (always fetch real-time, don't use latest from df)
    current_price = await get_current_price(ticker, verbose=False)
    if current_price is None:
        # Fallback to latest close only if real-time price unavailable
        current_price = df.iloc[-1]['close']
    
    sr_analyzer = SupportResistanceAnalyzer()
    supportAndResistanceData = await sr_analyzer.analyze_support_resistance(
        ticker=ticker,
        df=df,
        indicators=indicators,
        current_price=current_price
    )
    
    return supportAndResistanceData

