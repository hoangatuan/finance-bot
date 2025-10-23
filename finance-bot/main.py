#!/usr/bin/env python3
"""
Finance Bot - Main Entry Point
Integrates data fetching and technical analysis for Vietnamese stocks
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetcher.fetcher_factory import FetcherFactory
from indicators.ta import TechnicalAnalyzer
from indicators.pipeline import IndicatorPipeline


async def fetch_hpg_data():
    """Fetch HPG stock data for today and recent history"""
    print("🔍 Fetching HPG stock data...")
    
    try:
        # Create VNStock fetcher
        fetcher = FetcherFactory.create_fetcher('vnstock', rate_limit=60)
        
        # Get today's date and 30 days back for context
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        print(f"📅 Fetching data from {start_date} to {end_date}")
        
        # Fetch historical data
        historical_df = await fetcher.fetch_historical(
            ticker='HPG',
            start_date=start_date,
            end_date=end_date,
            interval='1D'
        )
        
        if historical_df.empty:
            print("❌ No historical data found for HPG")
            return None
        
        print(f"✅ Fetched {len(historical_df)} historical records")
        print(f"📊 Data columns: {list(historical_df.columns)}")
        
        # Show latest data
        latest_data = historical_df.iloc[-1]
        print(f"\n📈 Latest HPG Data:")
        print(f"   Date: {latest_data['timestamp'].strftime('%Y-%m-%d')}")
        print(f"   Open: {latest_data['open']:,.2f}")
        print(f"   High: {latest_data['high']:,.2f}")
        print(f"   Low: {latest_data['low']:,.2f}")
        print(f"   Close: {latest_data['close']:,.2f}")
        print(f"   Volume: {latest_data['volume']:,.0f}")
        
        return historical_df
        
    except Exception as e:
        print(f"❌ Error fetching HPG data: {e}")
        return None


async def run_technical_analysis(df: pd.DataFrame):
    """Run technical analysis on the fetched data"""
    print("\n🔬 Running Technical Analysis...")
    
    try:
        # Create technical analyzer and pipeline
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        # Process the data with technical indicators
        processed_df = await pipeline.process_historical_data(
            df, 'HPG',
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
        
        print(f"\n📊 Latest Technical Indicators for HPG:")
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


async def analyze_trading_signals(df: pd.DataFrame):
    """Analyze basic trading signals from the indicators"""
    print("\n🎯 Analyzing Trading Signals...")
    
    try:
        if df.empty:
            print("❌ No data for signal analysis")
            return
        
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
            
    except Exception as e:
        print(f"❌ Error analyzing trading signals: {e}")


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
    await analyze_trading_signals(analyzed_data)
    
    print("\n✅ Analysis completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 