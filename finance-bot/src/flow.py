"""
Multi-timeframe Analysis Flow
Facade pattern implementation - wraps complex multi-timeframe analysis logic
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import date, timedelta
import pandas as pd

try:
    from .fetcher.fetcher_factory import FetcherFactory
    from .indicators.ai_analyzer import OpenAIAnalyzer
    from .indicators.pipeline import IndicatorPipeline
    from .indicators.ta import TechnicalAnalyzer
    from .utils.ta_utils import analyze_support_resistance
    from .utils.data_fetcher import get_current_price
except ImportError:
    # Fallback for when running as script
    from fetcher.fetcher_factory import FetcherFactory
    from indicators.ai_analyzer import OpenAIAnalyzer
    from indicators.pipeline import IndicatorPipeline
    from indicators.ta import TechnicalAnalyzer
    from utils.ta_utils import analyze_support_resistance
    from utils.data_fetcher import get_current_price


def _get_adaptive_indicator_params(data_points: int, timeframe: str) -> Dict[str, Any]:
    """
    Calculate adaptive indicator parameters based on available data points and timeframe.
    
    Args:
        data_points: Number of data points available
        timeframe: Timeframe string (1M, 1W, 1D, 4H, etc.)
    
    Returns:
        Dictionary with indicator parameters:
        - sma_periods: List of SMA periods
        - rsi_period: RSI period
        - macd_fast: MACD fast period
        - macd_slow: MACD slow period
        - macd_signal: MACD signal period
    """
    # Default parameters for daily and lower timeframes (with sufficient data)
    default_sma_periods = [20, 50]
    default_rsi_period = 14
    default_macd_fast = 12
    default_macd_slow = 26
    default_macd_signal = 9
    
    # For monthly/weekly data or limited data points, use smaller periods
    if timeframe in ['1M', '1W'] or data_points < 50:
        # For monthly/weekly or limited data, use proportional periods
        # RSI: must be < data_points (strictly less)
        # SMA: can be <= data_points
        # MACD: slow must be < data_points
        
        # Calculate safe periods (leave some buffer)
        max_safe_period = max(3, data_points - 1)  # Leave at least 1 buffer for RSI
        
        # Adaptive SMA periods
        if data_points >= 20:
            sma_periods = [min(10, max_safe_period // 2), min(20, max_safe_period)]
        elif data_points >= 10:
            sma_periods = [min(5, max_safe_period // 2), min(10, max_safe_period)]
        else:
            sma_periods = [min(3, max_safe_period)]
        
        # Remove duplicates and sort
        sma_periods = sorted(list(set(sma_periods)))
        
        # Adaptive RSI period (must be < data_points, strictly less)
        rsi_period = min(default_rsi_period, max_safe_period)
        # Ensure RSI period is strictly less than data_points
        if rsi_period >= data_points:
            rsi_period = max(3, data_points - 1)
        
        # Adaptive MACD periods (slow must be < data_points)
        if data_points >= 26:
            macd_fast = default_macd_fast
            macd_slow = default_macd_slow
            macd_signal = default_macd_signal
        elif data_points >= 15:
            macd_fast = 5
            macd_slow = min(12, max_safe_period)
            macd_signal = 3
            # Ensure slow < data_points
            if macd_slow >= data_points:
                macd_slow = max(5, data_points - 1)
        elif data_points >= 9:
            macd_fast = 3
            macd_slow = min(6, max_safe_period)
            macd_signal = 2
            # Ensure slow < data_points
            if macd_slow >= data_points:
                macd_slow = max(3, data_points - 1)
        else:
            # Not enough data for MACD
            macd_fast = None
            macd_slow = None
            macd_signal = None
    else:
        # Use default parameters for daily/hourly with sufficient data
        sma_periods = default_sma_periods
        rsi_period = default_rsi_period
        macd_fast = default_macd_fast
        macd_slow = default_macd_slow
        macd_signal = default_macd_signal
    
    return {
        'sma_periods': sma_periods,
        'rsi_period': rsi_period,
        'macd_fast': macd_fast,
        'macd_slow': macd_slow,
        'macd_signal': macd_signal
    }


async def analyze_ticker_multi_timeframe(
    ticker: str,
    timeframes: Optional[List[str]] = None,
    days_back: Optional[Dict[str, int]] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a ticker across multiple timeframes.
    
    This function:
    1. Fetches data for each timeframe
    2. Performs technical analysis (TA) for each timeframe
    3. Analyzes support/resistance for each timeframe
    4. Aggregates all data and feeds to AI for final analysis
    
    Args:
        ticker: Stock symbol to analyze
        timeframes: List of timeframes to analyze. Default: ['1M', '1W', '1D', '4H']
        days_back: Dictionary mapping timeframe to days of history to fetch.
                  Default: {'1M': 365, '1W': 250, '1D': 250, '4H': 60}
        verbose: If True, print progress messages
    
    Returns:
        Dictionary containing:
        - ticker: Stock symbol
        - timeframes: Dictionary with analysis results for each timeframe
        - ai_analysis: AI-generated analysis based on all timeframes
        - summary: Summary of the analysis
    """
    # Default timeframes
    if timeframes is None:
        timeframes = ['1M', '1W', '1D', '4H']
    
    # Default days back for each timeframe
    if days_back is None:
        days_back = {
            '1M': 1825,   # ~5 year for monthly to get 50 months
            '1W': 250,   # ~1 year for weekly
            '1D': 250,   # ~1 year for daily
            '4H': 30,    # ~2 months for 4-hour
        }
    
    if verbose:
        print(f"\n🚀 Starting Multi-Timeframe Analysis for {ticker}")
        print("=" * 70)
        print(f"📊 Timeframes: {', '.join(timeframes)}")
    
    # Initialize results dictionary
    results = {
        'ticker': ticker,
        'timeframes': {},
        'ai_analysis': None,
        'summary': {}
    }
    
    # Create fetcher
    fetcher = FetcherFactory.create_fetcher('vnstock', rate_limit=60)
    
    # Get current price (used across all timeframes)
    current_price = await get_current_price(ticker, verbose=verbose)
    
    # Analyze each timeframe
    for timeframe in timeframes:
        if verbose:
            print(f"\n{'='*70}")
            print(f"📈 Analyzing {ticker} - {timeframe} timeframe")
            print(f"{'='*70}")
        
        try:
            # Determine days to fetch for this timeframe
            days = days_back.get(timeframe, 250)
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            if verbose:
                print(f"📥 Fetching {timeframe} data from {start_date} to {end_date} ({days} days)")
            
            # Fetch historical data for this timeframe
            # Note: 4H might not be directly supported, so we'll try it and handle gracefully
            interval = timeframe
            
            # Check if interval is valid, if not use fallback
            if interval == '4H' and not fetcher.validate_interval('4H'):
                if verbose:
                    print(f"⚠️  4H interval not supported, using 1H instead")
                interval = '1H'  # Use 1H as fallback
            
            try:
                historical_df = await fetcher.fetch_historical(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval
                )
            except (ValueError, Exception) as e:
                # If 4H fails and we haven't tried 1H yet, try 1H
                if timeframe == '4H' and interval == '4H':
                    if verbose:
                        print(f"⚠️  4H interval failed, using 1H instead: {e}")
                    interval = '1H'
                    historical_df = await fetcher.fetch_historical(
                        ticker=ticker,
                        start_date=start_date,
                        end_date=end_date,
                        interval='1H'
                    )
                else:
                    raise  # Re-raise if it's not a 4H issue
            
            if historical_df.empty:
                if verbose:
                    print(f"❌ No data fetched for {timeframe}")
                results['timeframes'][timeframe] = {
                    'error': 'No data available',
                    'interval_used': interval
                }
                continue
            
            if verbose:
                print(f"✅ Fetched {len(historical_df)} records for {timeframe}")
            
            # Sort by timestamp
            historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
            
            # Step 2: Run Technical Analysis with adaptive parameters
            if verbose:
                print(f"🔬 Running Technical Analysis for {timeframe}...")
            
            # Calculate adaptive indicator parameters based on data size
            data_points = len(historical_df)
            indicator_params = _get_adaptive_indicator_params(data_points, timeframe)
            
            if verbose and data_points < 50:
                print(f"   ⚠️  Limited data ({data_points} points), using adaptive parameters:")
                print(f"      SMA periods: {indicator_params['sma_periods']}")
                print(f"      RSI period: {indicator_params['rsi_period']}")
                if indicator_params['macd_fast']:
                    print(f"      MACD: {indicator_params['macd_fast']}/{indicator_params['macd_slow']}/{indicator_params['macd_signal']}")
                else:
                    print(f"      MACD: Skipped (insufficient data)")
            
            try:
                # Create technical analyzer and pipeline
                analyzer = TechnicalAnalyzer()
                pipeline = IndicatorPipeline(analyzer)
                
                # Process the data with adaptive indicator parameters
                processed_df = await pipeline.process_historical_data(
                    historical_df, ticker,
                    sma_periods=indicator_params['sma_periods'],
                    rsi_period=indicator_params['rsi_period'],
                    macd_fast=indicator_params['macd_fast'],
                    macd_slow=indicator_params['macd_slow'],
                    macd_signal=indicator_params['macd_signal']
                )
                
                if processed_df is None or processed_df.empty:
                    if verbose:
                        print(f"❌ Technical analysis failed for {timeframe}")
                    results['timeframes'][timeframe] = {
                        'error': 'Technical analysis failed',
                        'interval_used': interval
                    }
                    continue
                
                if verbose:
                    print(f"✅ Technical analysis completed: {len(processed_df)} records processed")
            
            except Exception as e:
                if verbose:
                    print(f"❌ Error in technical analysis for {timeframe}: {e}")
                    import traceback
                    traceback.print_exc()
                results['timeframes'][timeframe] = {
                    'error': f'Technical analysis error: {str(e)}',
                    'interval_used': interval
                }
                continue
            
            # Get latest indicators
            latest_indicators = processed_df.iloc[-1].to_dict()
            
            # Step 3: Analyze Support and Resistance
            if verbose:
                print(f"🛡️  Analyzing Support & Resistance for {timeframe}...")
            
            support_resistance_data = await analyze_support_resistance(
                ticker=ticker,
                df=processed_df,
                indicators=latest_indicators
            )
            
            # Store results for this timeframe
            results['timeframes'][timeframe] = {
                'interval_used': interval,
                'data_points': len(processed_df),
                'current_price': support_resistance_data.get('current_price', current_price),
                'indicators': latest_indicators,
                'support_resistance': support_resistance_data,
                'latest_data': processed_df.iloc[-1].to_dict() if not processed_df.empty else None
            }
            
            if verbose:
                print(f"✅ {timeframe} analysis completed:")
                print(f"   - Data points: {len(processed_df)}")
                print(f"   - Resistance levels: {len(support_resistance_data.get('resistance_levels', []))}")
                print(f"   - Support levels: {len(support_resistance_data.get('support_levels', []))}")
                if latest_indicators.get('rsi_14'):
                    print(f"   - RSI(14): {latest_indicators['rsi_14']:.2f}")
                if latest_indicators.get('sma_20'):
                    print(f"   - SMA(20): {latest_indicators['sma_20']:,.2f}")
        
        except Exception as e:
            if verbose:
                print(f"❌ Error analyzing {timeframe}: {e}")
                import traceback
                traceback.print_exc()
            results['timeframes'][timeframe] = {
                'error': str(e),
                'interval_used': interval if 'interval' in locals() else timeframe
            }
    
    # Step 4: Feed all data to AI for comprehensive analysis
    if verbose:
        print(f"\n{'='*70}")
        print(f"🤖 Generating AI Analysis from all timeframes")
        print(f"{'='*70}")
    
    try:
        # Check if OpenAI is configured
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            if verbose:
                print("⚠️  OpenAI API key not configured. Skipping AI analysis.")
                print("   Set OPENAI_API_KEY environment variable to enable AI analysis.")
            results['ai_analysis'] = {
                'error': 'OpenAI API key not configured'
            }
        else:
            # Prepare data for AI analysis
            ai_analyzer = OpenAIAnalyzer()
            
            # Get the most recent timeframe data (prefer 1D, then 1W, then others)
            primary_timeframe = None
            primary_data = None
            
            for tf in ['1D', '1W', '1M', '4H']:
                if tf in results['timeframes'] and 'error' not in results['timeframes'][tf]:
                    primary_timeframe = tf
                    primary_data = results['timeframes'][tf]
                    break
            
            if primary_data is None:
                # Use first available timeframe
                for tf, data in results['timeframes'].items():
                    if 'error' not in data:
                        primary_timeframe = tf
                        primary_data = data
                        break
            
            if primary_data is None:
                if verbose:
                    print("❌ No valid timeframe data available for AI analysis")
                results['ai_analysis'] = {
                    'error': 'No valid timeframe data available'
                }
            else:
                # Use primary timeframe data for AI
                current_price_ai = primary_data.get('current_price', current_price)
                indicators_ai = primary_data.get('indicators', {})
                zones_ai = primary_data.get('support_resistance', {})
                
                # Create enhanced prompt with multi-timeframe context
                multi_tf_context = _format_multi_timeframe_context(results['timeframes'], ticker)
                
                # Get AI suggestions
                ai_suggestions = await ai_analyzer.get_trading_suggestions(
                    ticker=ticker,
                    current_price=current_price_ai,
                    indicators=indicators_ai,
                    zones=zones_ai,
                    recent_price_action={
                        'multi_timeframe_context': multi_tf_context,
                        'timeframes_analyzed': list(results['timeframes'].keys())
                    }
                )
                
                results['ai_analysis'] = ai_suggestions
                
                if verbose:
                    print("✅ AI Analysis completed")
                    # Print formatted output
                    formatted_output = ai_analyzer.format_suggestions_output(ai_suggestions)
                    print(formatted_output)
    
    except Exception as e:
        if verbose:
            print(f"❌ Error in AI analysis: {e}")
            import traceback
            traceback.print_exc()
        results['ai_analysis'] = {
            'error': str(e)
        }
    
    # Create summary
    results['summary'] = {
        'ticker': ticker,
        'timeframes_analyzed': [tf for tf in timeframes if tf in results['timeframes']],
        'successful_timeframes': [
            tf for tf, data in results['timeframes'].items() 
            if 'error' not in data
        ],
        'failed_timeframes': [
            tf for tf, data in results['timeframes'].items() 
            if 'error' in data
        ],
        'current_price': current_price,
        'has_ai_analysis': results['ai_analysis'] is not None and 'error' not in results['ai_analysis']
    }
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"✅ Multi-Timeframe Analysis Complete for {ticker}")
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   - Timeframes analyzed: {len(results['summary']['successful_timeframes'])}/{len(timeframes)}")
        print(f"   - AI Analysis: {'✅' if results['summary']['has_ai_analysis'] else '❌'}")
        print(f"   - Current Price: {current_price:,.2f} VND" if current_price else "   - Current Price: N/A")
    
    return results


def _format_multi_timeframe_context(timeframes_data: Dict[str, Any], ticker: str) -> str:
    """
    Format multi-timeframe context for AI analysis
    
    Args:
        timeframes_data: Dictionary with analysis results for each timeframe
        ticker: Stock symbol
    
    Returns:
        Formatted string with multi-timeframe context
    """
    lines = [f"## Multi-Timeframe Analysis Context for {ticker}"]
    
    for timeframe, data in timeframes_data.items():
        if 'error' in data:
            lines.append(f"\n### {timeframe} Timeframe: ❌ Error - {data['error']}")
            continue
        
        lines.append(f"\n### {timeframe} Timeframe ({data.get('interval_used', timeframe)}):")
        lines.append(f"- Data Points: {data.get('data_points', 0)}")
        
        indicators = data.get('indicators', {})
        if indicators:
            if indicators.get('rsi_14'):
                lines.append(f"- RSI(14): {indicators['rsi_14']:.2f}")
            if indicators.get('sma_20'):
                lines.append(f"- SMA(20): {indicators['sma_20']:,.2f}")
            if indicators.get('sma_50'):
                lines.append(f"- SMA(50): {indicators['sma_50']:,.2f}")
            if indicators.get('macd'):
                lines.append(f"- MACD: {indicators['macd']:.2f}")
        
        sr_data = data.get('support_resistance', {})
        if sr_data:
            resistance_levels = sr_data.get('resistance_levels', [])
            support_levels = sr_data.get('support_levels', [])
            lines.append(f"- Resistance Levels: {len(resistance_levels)}")
            lines.append(f"- Support Levels: {len(support_levels)}")
            
            if resistance_levels:
                nearest_res = resistance_levels[0]
                lines.append(f"  - Nearest Resistance: {nearest_res.get('price', 0):,.2f} "
                           f"({nearest_res.get('strength', 'N/A')} strength, "
                           f"{nearest_res.get('touch_count', 0)} touches)")
            
            if support_levels:
                nearest_sup = support_levels[0]
                lines.append(f"  - Nearest Support: {nearest_sup.get('price', 0):,.2f} "
                           f"({nearest_sup.get('strength', 'N/A')} strength, "
                           f"{nearest_sup.get('touch_count', 0)} touches)")
    
    return "\n".join(lines)

