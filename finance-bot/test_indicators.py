#!/usr/bin/env python3
"""
Test script for Technical Analysis indicators
"""
import asyncio
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators.ta import TechnicalAnalyzer
from indicators.pipeline import IndicatorPipeline
from fetcher.vnstock_fetcher import VNStockFetcher


def create_sample_data(ticker: str = 'TEST', days: int = 100) -> pd.DataFrame:
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # Generate realistic price data
    np.random.seed(42)  # For reproducible results
    
    # Start with base price
    base_price = 100.0
    prices = []
    
    for i in range(days):
        # Random walk with trend
        if i == 0:
            price = base_price
        else:
            change = np.random.normal(0.001, 0.02)  # Small daily change
            price = prices[-1] * (1 + change)
        
        # Generate OHLC from close price
        daily_volatility = np.random.uniform(0.01, 0.03)
        high = price * (1 + daily_volatility)
        low = price * (1 - daily_volatility)
        open_price = price * (1 + np.random.uniform(-0.01, 0.01))
        close = price
        
        # Generate volume
        volume = np.random.randint(1000000, 10000000)
        
        prices.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'source': 'test',
            'data_type': 'historical',
            'interval': '1D'
        })
    
    return pd.DataFrame(prices)


async def test_technical_analyzer():
    """Test Technical Analyzer"""
    print("Testing Technical Analyzer...")
    
    try:
        # Create analyzer
        analyzer = TechnicalAnalyzer()
        
        # Create sample data
        df = create_sample_data('VNM', 100)
        print(f"✅ Created sample data: {len(df)} records")
        
        # Test data validation
        is_valid, errors = analyzer.validate_data_quality(df)
        print(f"✅ Data validation: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            print(f"   Errors: {errors}")
        
        # Test SMA calculation
        print("\nTesting SMA calculation...")
        sma_data = await analyzer.calculate_sma(df['close'], [20, 50])
        print(f"✅ SMA calculated: {list(sma_data.keys())}")
        
        # Test RSI calculation
        print("\nTesting RSI calculation...")
        rsi_data = await analyzer.calculate_rsi(df['close'], 14)
        print(f"✅ RSI calculated: length={len(rsi_data)}, last_value={rsi_data.iloc[-1]:.2f}")
        
        # Test MACD calculation
        print("\nTesting MACD calculation...")
        macd_data = await analyzer.calculate_macd(df['close'], 12, 26, 9)
        print(f"✅ MACD calculated: {list(macd_data.keys())}")
        
        # Test volume analysis
        print("\nTesting volume analysis...")
        volume_data = await analyzer.calculate_volume_analysis(df)
        print(f"✅ Volume analysis: {list(volume_data.keys())}")
        
        # Test all indicators together
        print("\nTesting all indicators together...")
        all_indicators = await analyzer.calculate_all_indicators(
            df, 'VNM',
            sma_periods=[20, 50],
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )
        
        print(f"✅ All indicators calculated: {len(all_indicators)} total")
        print(f"   Metadata: {all_indicators.get('metadata', {})}")
        
        # Show some indicator values
        if 'sma_20' in all_indicators:
            sma_20 = all_indicators['sma_20']
            print(f"   SMA(20) last value: {sma_20.iloc[-1]:.2f}")
        
        if 'rsi_14' in all_indicators:
            rsi_14 = all_indicators['rsi_14']
            print(f"   RSI(14) last value: {rsi_14.iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing technical analyzer: {e}")
        return False


async def test_indicator_pipeline():
    """Test Indicator Pipeline"""
    print("\nTesting Indicator Pipeline...")
    
    try:
        # Create analyzer and pipeline
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        # Create sample data
        df = create_sample_data('HPG', 100)
        print(f"✅ Created sample data: {len(df)} records")
        
        # Test historical data processing
        print("\nTesting historical data processing...")
        processed_df = await pipeline.process_historical_data(
            df, 'HPG',
            sma_periods=[20, 50],
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )
        
        print(f"✅ Historical data processed: {len(processed_df)} records")
        print(f"   Columns: {list(processed_df.columns)}")
        
        # Validate processed data
        expected_indicators = ['sma_20', 'sma_50', 'rsi_14', 'macd', 'macd_signal', 'macd_histogram']
        is_valid, errors = pipeline.validate_processed_data(processed_df, expected_indicators)
        print(f"✅ Processed data validation: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            print(f"   Errors: {errors}")
        
        # Get indicators summary
        summary = pipeline.get_indicators_summary(processed_df)
        print(f"✅ Indicators summary generated: {len(summary)} indicators")
        
        # Show some summary stats
        for indicator, stats in list(summary.items())[:3]:  # Show first 3
            print(f"   {indicator}: mean={stats['mean']:.2f}, last={stats['last_value']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing indicator pipeline: {e}")
        return False


async def test_custom_parameters():
    """Test custom parameters for different stocks"""
    print("\nTesting Custom Parameters...")
    
    try:
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        # Create data for different stocks
        vnm_data = create_sample_data('VNM', 100)
        hpg_data = create_sample_data('HPG', 100)
        
        # VNM with default parameters
        print("Testing VNM with default parameters...")
        vnm_processed = await pipeline.process_historical_data(vnm_data, 'VNM')
        print(f"✅ VNM processed: {len(vnm_processed)} records")
        
        # HPG with custom parameters
        print("Testing HPG with custom parameters...")
        hpg_processed = await pipeline.process_historical_data(
            hpg_data, 'HPG',
            sma_periods=[10, 30],      # Custom SMA periods
            rsi_period=21,              # Custom RSI period
            macd_fast=8,                # Custom MACD fast
            macd_slow=21,               # Custom MACD slow
            volume_avg_period=15        # Custom volume period
        )
        print(f"✅ HPG processed with custom params: {len(hpg_processed)} records")
        
        # Compare parameters used
        vnm_indicators = [col for col in vnm_processed.columns if col.startswith(('sma_', 'rsi_', 'macd_', 'volume_'))]
        hpg_indicators = [col for col in hpg_processed.columns if col.startswith(('sma_', 'rsi_', 'macd_', 'volume_'))]
        
        print(f"   VNM indicators: {vnm_indicators}")
        print(f"   HPG indicators: {hpg_indicators}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing custom parameters: {e}")
        return False


async def test_batch_processing():
    """Test batch processing for multiple tickers"""
    print("\nTesting Batch Processing...")
    
    try:
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        # Create data for multiple tickers
        tickers_data = {
            'VNM': create_sample_data('VNM', 100),
            'HPG': create_sample_data('HPG', 100),
            'VCB': create_sample_data('VCB', 100)
        }
        
        print(f"✅ Created data for {len(tickers_data)} tickers")
        
        # Process all tickers with same parameters
        results = await pipeline.process_multiple_tickers(
            tickers_data,
            sma_periods=[20, 50],
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )
        
        print(f"✅ Batch processing completed: {len(results)} tickers")
        
        # Show results for each ticker
        for ticker, result_df in results.items():
            if not result_df.empty:
                indicator_count = len([col for col in result_df.columns if col.startswith(('sma_', 'rsi_', 'macd_', 'volume_'))])
                print(f"   {ticker}: {len(result_df)} records, {indicator_count} indicators")
            else:
                print(f"   {ticker}: FAILED")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing batch processing: {e}")
        return False


async def test_integration_with_vnstock():
    """Test integration with VNStock fetcher"""
    print("\nTesting Integration with VNStock...")
    
    try:
        # Create fetcher
        fetcher = VNStockFetcher(rate_limit=60)
        
        # Fetch historical data
        print("Fetching VNM historical data...")
        historical_df = await fetcher.fetch_historical(
            ticker='VNM',
            start_date='2024-01-01',
            end_date='2024-01-31',
            interval='1D'
        )
        
        if historical_df.empty:
            print("❌ No historical data fetched")
            return False
        
        print(f"✅ Fetched {len(historical_df)} historical records")
        
        # Process with indicators
        analyzer = TechnicalAnalyzer()
        pipeline = IndicatorPipeline(analyzer)
        
        processed_df = await pipeline.process_historical_data(
            historical_df, 'VNM',
            sma_periods=[20, 50],
            rsi_period=14
        )
        
        print(f"✅ Processed VNM data: {len(processed_df)} records")
        print(f"   Columns: {list(processed_df.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing VNStock integration: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Technical Analysis Tests...\n")
    
    # Run tests
    tests = [
        test_technical_analyzer,
        test_indicator_pipeline,
        test_custom_parameters,
        test_batch_processing,
        test_integration_with_vnstock
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")
    
    return passed == total


if __name__ == "__main__":
    # Run async tests
    asyncio.run(main())
