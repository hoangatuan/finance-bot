#!/usr/bin/env python3
"""
Finance Bot - Main Entry Point
Integrates data fetching and technical analysis for Vietnamese stocks
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators.ai_analyzer import OpenAIAnalyzer
from indicators.visualization import SupportResistanceVisualizer
from utils.data_fetcher import fetch_extended_historical, get_current_price
from utils.ta_utils import run_technical_analysis, analyze_support_resistance
from utils.ai_utils import get_ai_suggestions
from portfolio.analyzer import run_daily_analysis
from portfolio.formatter import format_portfolio_analysis
from flow import analyze_ticker_multi_timeframe


async def fetch_hpg_data():
    """Fetch HPG stock data for today and recent history (legacy function)"""
    return await fetch_extended_historical('HPG', days=30)


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
        current_price = await get_current_price(ticker)
        if current_price is None:
            current_price = historical_df.iloc[-1]['close']
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
        supportAndResistanceData = await analyze_support_resistance(ticker, processed_df, latest_indicators)
        
        if supportAndResistanceData:
            print(f"\n✅ Support/Resistance analysis completed successfully!")
            print(f"   Found {len(supportAndResistanceData.get('resistance_levels', []))} resistance levels")
            print(f"   Found {len(supportAndResistanceData.get('support_levels', []))} support levels")
            
            # Step 5.5: Visualize the chart
            print(f"\n📊 Step 5: Generating visualization...")
            try:
                visualizer = SupportResistanceVisualizer(figsize=(16, 10), dpi=100)
                
                # Create charts directory if it doesn't exist
                charts_dir = os.path.join(os.path.dirname(__file__), 'charts')
                os.makedirs(charts_dir, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(charts_dir, f'{ticker}_sr_{timestamp_str}.png')
                
                # Plot the chart
                visualizer.plot_chart(
                    df=processed_df,
                    support_resistance_data=supportAndResistanceData,
                    ticker=ticker,
                    save_path=save_path,
                    show=False  # Don't show interactively, just save
                )
                print(f"✅ Chart saved to: {save_path}")
            except Exception as e:
                print(f"⚠️  Error generating visualization: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n⚠️  Support/Resistance analysis completed with warnings")
        
        # Step 6: Get AI suggestions - pass supportAndResistanceData to AI
        if supportAndResistanceData:
            await get_ai_suggestions(
                ticker=ticker,
                current_price=supportAndResistanceData.get('current_price', current_price),
                indicators=latest_indicators,
                zones=supportAndResistanceData,  # Pass the full supportAndResistanceData
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
    
    # Step 3: Get AI suggestions (if OpenAI API key is configured)
    # AI will analyze indicators directly without manual signal analysis
    latest_indicators = analyzed_data.iloc[-1].to_dict()
    current_price = await get_current_price('HPG')
    if current_price is None:
        current_price = analyzed_data.iloc[-1]['close']
    
    # Get basic zones for AI analysis (simplified version)
    zones = {'resistance_zones': [], 'support_zones': []}
    
    await get_ai_suggestions(
        ticker='HPG',
        current_price=current_price,
        indicators=latest_indicators,
        zones=zones,
        df=analyzed_data
    )
    
    print("\n✅ Analysis completed successfully!")
    print("=" * 50)


async def analyze_portfolio(portfolio_path: str = None, include_ai: bool = True):
    """
    Analyze portfolio with technical analysis and AI advice
    
    Args:
        portfolio_path: Path to portfolio JSON file. If None, uses default.
        include_ai: If True, include AI portfolio advice
    """
    print("🚀 Portfolio Analysis")
    print("=" * 70)
    
    try:
        # Run daily analysis
        analysis_result = await run_daily_analysis(
            portfolio_path=portfolio_path,
            days_history=250,
            verbose=True
        )
        
        ai_advice = None
        
        # Get AI advice if requested and OpenAI is configured
        if include_ai:
            try:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    print("\n🤖 Getting AI Portfolio Advice...")
                    ai_analyzer = OpenAIAnalyzer()
                    ai_advice = await ai_analyzer.get_portfolio_advice(
                        portfolio_data=analysis_result.get("portfolio", {}),
                        ta_results=analysis_result.get("ta_results", {}),
                        portfolio_summary=analysis_result.get("portfolio_summary", {})
                    )
                else:
                    print("\n⚠️  OpenAI API key not configured. Skipping AI advice.")
                    print("   Set OPENAI_API_KEY environment variable to enable AI analysis.")
            except Exception as e:
                print(f"\n⚠️  Error getting AI advice: {e}")
        
        # Format and display results
        formatted_output = format_portfolio_analysis(analysis_result, ai_advice)
        print(formatted_output)
        
    except Exception as e:
        print(f"\n❌ Error analyzing portfolio: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'analyze' or command == '--analyze':
            # Multi-timeframe analysis (new main flow)
            ticker = sys.argv[2] if len(sys.argv) > 2 else 'HPG'
            asyncio.run(analyze_ticker_multi_timeframe(ticker, verbose=True))
        elif command == '--test-sr':
            # Support/resistance test
            ticker = sys.argv[2] if len(sys.argv) > 2 else 'HPG'
            asyncio.run(test_support_resistance_analysis(ticker))
        elif command == '--visualize-sr':
            # Support/resistance visualization
            ticker = sys.argv[2] if len(sys.argv) > 2 else 'HPG'
            asyncio.run(test_support_resistance_analysis(ticker))
        elif command == 'analyze-portfolio':
            # Portfolio analysis
            portfolio_path = sys.argv[2] if len(sys.argv) > 2 else None
            include_ai = '--no-ai' not in sys.argv
            asyncio.run(analyze_portfolio(portfolio_path=portfolio_path, include_ai=include_ai))
        else:
            # Default: run main function
            asyncio.run(main())
    else:
        # Default: run multi-timeframe analysis for HPG
        asyncio.run(analyze_ticker_multi_timeframe('HPG', verbose=True)) 