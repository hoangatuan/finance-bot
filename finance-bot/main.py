#!/usr/bin/env python3
"""
Finance Bot - Main Entry Point
Integrates data fetching and technical analysis for Vietnamese stocks
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators.ta import TechnicalAnalyzer
from indicators.pipeline import IndicatorPipeline
from indicators.support_resistance import SupportResistanceAnalyzer
from indicators.ai_analyzer import OpenAIAnalyzer
from utils.data_fetcher import fetch_extended_historical, get_current_price


async def fetch_hpg_data():
    """Fetch HPG stock data for today and recent history (legacy function)"""
    return await fetch_extended_historical('HPG', days=30)


async def run_technical_analysis(df: pd.DataFrame, ticker: str = None):
    """
    Run technical analysis on the fetched data
    
    Args:
        df: DataFrame with historical data
        ticker: Stock symbol (auto-detected from df if not provided)
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
    Analyze support and resistance zones with confidence scoring
    
    Args:
        ticker: Stock symbol
        df: DataFrame with historical data and indicators
        indicators: Dictionary with latest indicator values
    """
    print("\n🛡️ Analyzing Support & Resistance Zones...")
    
    try:
        # Get current price (validate against historical)
        historical_close = df.iloc[-1]['close']
        current_price = await get_current_price(ticker, historical_close)
        if current_price is None:
            current_price = historical_close
            print(f"📊 Using latest historical close as current price: {current_price:,.2f}")
        
        # Create SR analyzer
        sr_analyzer = SupportResistanceAnalyzer()
        
        # Find pivots
        print("🔍 Finding pivot points...")
        pivots = await sr_analyzer.find_pivots(df, left_bars=5, right_bars=5)
        print(f"   Found {len(pivots['pivot_highs'])} pivot highs and {len(pivots['pivot_lows'])} pivot lows")
        
        # Create zones (include touching levels detection for consolidation zones)
        print("🗺️  Creating pivot zones...")
        zones = await sr_analyzer.create_pivot_zones(
            pivots,
            current_price,
            df=df,  # Pass DataFrame for touching levels detection
            tolerance_percent=1.5,
            min_touches=2,
            include_touching_levels=True  # Enable consolidation zone detection
        )
        
        # Display zones
        print(f"\n📊 Support & Resistance Analysis for {ticker}:")
        print(f"   Current Price: {current_price:,.2f}")
        
        # Display resistance zones
        print(f"\n⚡ Resistance Zones (nearest above current price):")
        if zones['resistance_zones']:
            for i, zone in enumerate(zones['resistance_zones'][:3], 1):
                print(f"   {i}. Zone: {zone['lower']:,.2f} - {zone['upper']:,.2f} (Middle: {zone['middle']:,.2f})")
                print(f"      Distance: {zone['distance_pct']:.2f}% above | Strength: {zone['strength']:.2f} | Touches: {zone['touch_count']}")
        else:
            print("   No resistance zones found")
        
        # Display support zones
        print(f"\n🛡️ Support Zones (nearest below current price):")
        if zones['support_zones']:
            for i, zone in enumerate(zones['support_zones'][:3], 1):
                print(f"   {i}. Zone: {zone['lower']:,.2f} - {zone['upper']:,.2f} (Middle: {zone['middle']:,.2f})")
                print(f"      Distance: {zone['distance_pct']:.2f}% below | Strength: {zone['strength']:.2f} | Touches: {zone['touch_count']}")
        else:
            print("   No support zones found")
        
        # Calculate confidence for nearest zones
        print(f"\n🎯 Breakout Confidence Analysis:")
        
        # Nearest resistance
        if zones['resistance_zones']:
            nearest_resistance = zones['resistance_zones'][0]
            resistance_confidence = await sr_analyzer.calculate_breakout_confidence(
                nearest_resistance,
                indicators,
                df,
                is_resistance=True
            )
            
            print(f"\n   Nearest Resistance: {nearest_resistance['middle']:,.2f}")
            print(f"   Confidence Score: {resistance_confidence['confidence_score']:.2f} / 1.00")
            print(f"   Interpretation: {resistance_confidence['interpretation']}")
            print(f"   Breakdown:")
            print(f"      Volume Strength: {resistance_confidence['breakdown']['volume_strength']:.2f}")
            print(f"      Zone Strength: {resistance_confidence['breakdown']['zone_strength']:.2f}")
            print(f"      Momentum Strength: {resistance_confidence['breakdown']['momentum_strength']:.2f}")
            print(f"      Pattern Strength: {resistance_confidence['breakdown']['pattern_strength']:.2f}")
        
        # Nearest support
        if zones['support_zones']:
            nearest_support = zones['support_zones'][0]
            support_confidence = await sr_analyzer.calculate_breakout_confidence(
                nearest_support,
                indicators,
                df,
                is_resistance=False
            )
            
            print(f"\n   Nearest Support: {nearest_support['middle']:,.2f}")
            print(f"   Confidence Score: {support_confidence['confidence_score']:.2f} / 1.00")
            print(f"   Interpretation: {support_confidence['interpretation']}")
            print(f"   Breakdown:")
            print(f"      Volume Strength: {support_confidence['breakdown']['volume_strength']:.2f}")
            print(f"      Zone Strength: {support_confidence['breakdown']['zone_strength']:.2f}")
            print(f"      Momentum Strength: {support_confidence['breakdown']['momentum_strength']:.2f}")
            print(f"      Pattern Strength: {support_confidence['breakdown']['pattern_strength']:.2f}")
        
        return zones
        
    except Exception as e:
        print(f"❌ Error analyzing support/resistance: {e}")
        import traceback
        traceback.print_exc()
        return None


async def analyze_trading_signals(df: pd.DataFrame):
    """Analyze basic trading signals from the indicators"""
    print("\n🎯 Analyzing Trading Signals...")
    
    try:
        if df.empty:
            print("❌ No data for signal analysis")
            return []
        
        latest = df.iloc[-1]
        close_price = latest['close']
        
        signals = []
        
        # RSI Analysis
        rsi = latest.get('rsi_14')
        if pd.notna(rsi):
            if rsi < 30:
                signals.append("🔴 RSI Oversold (< 30) - Potential Buy Signal")
            elif rsi > 70:
                signals.append("🟡 RSI Overbought (> 70) - Potential Sell Signal")
            else:
                signals.append(f"🟢 RSI Neutral ({rsi:.1f})")
        
        # SMA Analysis
        sma_20 = latest.get('sma_20')
        sma_50 = latest.get('sma_50')
        
        if pd.notna(sma_20) and pd.notna(sma_50):
            if close_price > sma_20 > sma_50:
                signals.append("🟢 Bullish Trend - Price above both SMAs")
            elif close_price < sma_20 < sma_50:
                signals.append("🔴 Bearish Trend - Price below both SMAs")
            elif close_price > sma_20:
                signals.append("🟡 Mixed - Price above SMA(20) but below SMA(50)")
            else:
                signals.append("🟡 Mixed - Price below SMA(20)")
        
        # MACD Analysis
        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        
        if pd.notna(macd) and pd.notna(macd_signal):
            if macd > macd_signal:
                signals.append("🟢 MACD Bullish - MACD above Signal")
            else:
                signals.append("🔴 MACD Bearish - MACD below Signal")
        
        # Volume Analysis
        volume_ratio = latest.get('volume_ratio')
        if pd.notna(volume_ratio):
            if volume_ratio > 1.5:
                signals.append("📈 High Volume - Above average trading activity")
            elif volume_ratio < 0.5:
                signals.append("📉 Low Volume - Below average trading activity")
        
        print("📊 Trading Signals:")
        for signal in signals:
            print(f"   {signal}")
        
        if not signals:
            print("   ⚪ No clear signals detected")
        
        return signals
            
    except Exception as e:
        print(f"❌ Error analyzing trading signals: {e}")
        return []


async def get_ai_suggestions(
    ticker: str,
    current_price: float,
    indicators: Dict,
    zones: Dict,
    signals: List[str],
    df: pd.DataFrame
):
    """
    Get AI trading suggestions from OpenAI based on technical analysis
    
    Args:
        ticker: Stock symbol
        current_price: Current stock price
        indicators: Dictionary with latest indicator values
        zones: Dictionary with support/resistance zones
        signals: List of trading signals
        df: DataFrame with historical data for recent price action
    
    Returns:
        Dictionary with AI suggestions or None if error/not configured
    """
    try:
        # Check if OpenAI API key is configured
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("\n⚠️  OpenAI API key not configured. Skipping AI suggestions.")
            print("   Set OPENAI_API_KEY environment variable to enable AI analysis.")
            return None
        
        print("\n🤖 Getting AI Trading Suggestions...")
        
        # Create AI analyzer
        ai_analyzer = OpenAIAnalyzer()
        
        # Get recent price action
        recent_price_action = None
        if not df.empty and len(df) >= 10:
            recent_price_action = {
                'high': df['high'].tail(10).max(),
                'low': df['low'].tail(10).min(),
                'trend': 'uptrend' if df['close'].iloc[-1] > df['close'].iloc[-10] else 'downtrend'
            }
        
        # Get AI suggestions
        suggestions = await ai_analyzer.get_trading_suggestions(
            ticker=ticker,
            current_price=current_price,
            indicators=indicators,
            zones=zones,
            signals=signals,
            recent_price_action=recent_price_action
        )
        
        # Display formatted output
        if suggestions and 'error' not in suggestions:
            formatted_output = ai_analyzer.format_suggestions_output(suggestions)
            print(formatted_output)
        elif suggestions and 'error' in suggestions:
            print(f"❌ Error getting AI suggestions: {suggestions['error']}")
            return None
        else:
            print("❌ No suggestions returned from AI")
            return None
        
        return suggestions
        
    except ValueError as e:
        # API key not configured - this is okay, just skip
        print(f"\n⚠️  {str(e)}")
        return None
    except Exception as e:
        print(f"\n❌ Error getting AI suggestions: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_support_resistance_analysis(ticker: str = 'HPG'):
    """
    Test function for support/resistance analysis with extended data
    
    Args:
        ticker: Stock symbol to analyze (default: HPG)
    """
    print(f"\n🧪 Testing Support & Resistance Analysis for {ticker}")
    print("=" * 70)
    
    try:
        # Step 1: Fetch extended historical data (200+ days for pivot analysis)
        print(f"\n📥 Step 1: Fetching extended historical data...")
        historical_df = await fetch_extended_historical(ticker, days=250)
        if historical_df is None:
            print(f"❌ Failed to fetch data for {ticker}")
            return
        
        # Step 2: Get current price
        print(f"\n💰 Step 2: Getting current price...")
        historical_close = historical_df.iloc[-1]['close']
        current_price = await get_current_price(ticker, historical_close)
        if current_price is None:
            current_price = historical_close
            print(f"📊 Using latest historical close: {current_price:,.2f}")
        
        # Step 3: Run technical analysis
        print(f"\n📈 Step 3: Running technical analysis...")
        processed_df = await run_technical_analysis(historical_df, ticker)
        if processed_df is None:
            print("❌ Failed to run technical analysis")
            return
        
        # Step 4: Get latest indicators
        latest_indicators = processed_df.iloc[-1].to_dict()
        
        # Step 5: Analyze support and resistance
        print(f"\n🛡️ Step 4: Analyzing support & resistance zones...")
        zones = await analyze_support_resistance(ticker, processed_df, latest_indicators)
        
        if zones:
            print(f"\n✅ Support/Resistance analysis completed successfully!")
            print(f"   Found {len(zones['resistance_zones'])} resistance zones")
            print(f"   Found {len(zones['support_zones'])} support zones")
        else:
            print(f"\n⚠️  Support/Resistance analysis completed with warnings")
        
        # Step 6: Get trading signals
        signals = await analyze_trading_signals(processed_df)
        
        # Step 7: Get AI suggestions
        if zones:
            await get_ai_suggestions(
                ticker=ticker,
                current_price=current_price,
                indicators=latest_indicators,
                zones=zones,
                signals=signals or [],
                df=processed_df
            )
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error in support/resistance test: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function to run the finance bot"""
    print("🚀 Finance Bot - HPG Stock Analysis")
    print("=" * 50)
    
    # Step 1: Fetch HPG data
    hpg_data = await fetch_hpg_data()
    if hpg_data is None:
        print("❌ Failed to fetch HPG data. Exiting.")
        return
    
    # Step 2: Run technical analysis
    analyzed_data = await run_technical_analysis(hpg_data)
    if analyzed_data is None:
        print("❌ Failed to run technical analysis. Exiting.")
        return
    
    # Step 3: Analyze trading signals
    signals = await analyze_trading_signals(analyzed_data)
    
    # Step 4: Get AI suggestions (if OpenAI API key is configured)
    latest_indicators = analyzed_data.iloc[-1].to_dict()
    historical_close = analyzed_data.iloc[-1]['close']
    current_price = await get_current_price('HPG', historical_close)
    if current_price is None:
        current_price = historical_close
    
    # Get basic zones for AI analysis (simplified version)
    zones = {'resistance_zones': [], 'support_zones': []}
    
    await get_ai_suggestions(
        ticker='HPG',
        current_price=current_price,
        indicators=latest_indicators,
        zones=zones,
        signals=signals or [],
        df=analyzed_data
    )
    
    print("\n✅ Analysis completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    import sys
    
    # Check if user wants to run SR analysis test
    if len(sys.argv) > 1 and sys.argv[1] == '--test-sr':
        ticker = sys.argv[2] if len(sys.argv) > 2 else 'HPG'
        asyncio.run(test_support_resistance_analysis(ticker))
    else:
        # Run the async main function
        asyncio.run(main()) 