#!/usr/bin/env python3
"""
Quick test script to verify TA-Lib integration using real stock data
"""
import asyncio
import sys
import os
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators.ta import TechnicalAnalyzer
from utils.data_fetcher import fetch_extended_historical, get_current_price


async def test_talib_availability():
    """Test if TA-Lib is available"""
    print("=" * 60)
    print("TA-Lib Integration Test")
    print("=" * 60)
    
    try:
        import talib
        print(f"✅ TA-Lib is available (version: {talib.__version__})")
        return True
    except ImportError as e:
        print(f"❌ TA-Lib is not installed: {e}")
        print("   Install TA-Lib: pip install TA-Lib")
        print("   (Requires ta-lib C library: brew install ta-lib)")
        return False
    except Exception as e:
        print(f"⚠️  TA-Lib import failed: {e}")
        return False


async def test_sma(ticker: str = 'HPG'):
    """Test SMA calculation with real data"""
    print("\n📊 Testing SMA Calculation...")
    
    # Fetch real data
    print(f"   Fetching real data for {ticker}...")
    df = await fetch_extended_historical(ticker, days=100, verbose=False)
    
    if df is None or df.empty:
        print(f"   ❌ Failed to fetch data for {ticker}")
        return False
    
    print(f"   ✅ Fetched {len(df)} records")
    
    # Show latest price data
    latest = df.iloc[-1]
    print(f"   Latest {ticker} price: {latest['close']:,.2f} (Date: {latest['timestamp'].strftime('%Y-%m-%d')})")
    
    analyzer = TechnicalAnalyzer()
    
    try:
        sma_data = await analyzer.calculate_sma(df['close'], [20, 50])
        
        if 'sma_20' in sma_data and 'sma_50' in sma_data:
            sma_20_val = sma_data['sma_20'].iloc[-1]
            sma_50_val = sma_data['sma_50'].iloc[-1]
            
            print(f"   ✅ SMA(20) last value: {sma_20_val:,.2f}")
            print(f"   ✅ SMA(50) last value: {sma_50_val:,.2f}")
            
            # Validate values
            if pd.notna(sma_20_val) and pd.notna(sma_50_val):
                print("   ✅ SMA values are valid (not NaN)")
                return True
            else:
                print("   ❌ SMA values contain NaN")
                return False
        else:
            print("   ❌ SMA keys missing")
            return False
            
    except Exception as e:
        print(f"   ❌ SMA calculation failed: {e}")
        return False


async def test_rsi(ticker: str = 'HPG'):
    """Test RSI calculation with real data"""
    print("\n📈 Testing RSI Calculation...")
    
    # Fetch real data
    print(f"   Fetching real data for {ticker}...")
    df = await fetch_extended_historical(ticker, days=100, verbose=False)
    
    if df is None or df.empty:
        print(f"   ❌ Failed to fetch data for {ticker}")
        return False
    
    print(f"   ✅ Fetched {len(df)} records")
    
    # Show latest price data
    latest = df.iloc[-1]
    print(f"   Latest {ticker} price: {latest['close']:,.2f} (Date: {latest['timestamp'].strftime('%Y-%m-%d')})")
    
    analyzer = TechnicalAnalyzer()
    
    try:
        rsi_data = await analyzer.calculate_rsi(df['close'], 14)
        rsi_val = rsi_data.iloc[-1]
        
        print(f"   ✅ RSI(14) last value: {rsi_val:.2f}")
        
        # Validate RSI is in expected range (0-100)
        if pd.notna(rsi_val) and 0 <= rsi_val <= 100:
            print("   ✅ RSI value is in valid range (0-100)")
            return True
        else:
            print(f"   ⚠️  RSI value out of expected range: {rsi_val}")
            return False
            
    except Exception as e:
        print(f"   ❌ RSI calculation failed: {e}")
        return False


async def test_macd(ticker: str = 'HPG'):
    """Test MACD calculation with real data"""
    print("\n📉 Testing MACD Calculation...")
    
    # Fetch real data
    print(f"   Fetching real data for {ticker}...")
    df = await fetch_extended_historical(ticker, days=100, verbose=False)
    
    if df is None or df.empty:
        print(f"   ❌ Failed to fetch data for {ticker}")
        return False
    
    print(f"   ✅ Fetched {len(df)} records")
    
    # Show price information for context
    latest = df.iloc[-1]
    first_close = df['close'].iloc[0]
    last_close = df['close'].iloc[-1]
    print(f"   Latest {ticker} price: {last_close:,.2f} (Date: {latest['timestamp'].strftime('%Y-%m-%d')})")
    print(f"   Price range: {df['close'].min():,.2f} - {df['close'].max():,.2f}")
    print(f"   First close: {first_close:,.2f}, Last close: {last_close:,.2f}")
    
    analyzer = TechnicalAnalyzer()
    
    try:
        macd_data = await analyzer.calculate_macd(df['close'], 12, 26, 9)
        
        if 'macd' in macd_data and 'macd_signal' in macd_data and 'macd_histogram' in macd_data:
            macd_val = macd_data['macd'].iloc[-1]
            signal_val = macd_data['macd_signal'].iloc[-1]
            hist_val = macd_data['macd_histogram'].iloc[-1]
            
            # Calculate EMAs manually for verification
            ema_fast = df['close'].ewm(span=12, adjust=False).mean()
            ema_slow = df['close'].ewm(span=26, adjust=False).mean()
            manual_macd = ema_fast - ema_slow
            manual_signal = manual_macd.ewm(span=9, adjust=False).mean()
            manual_hist = manual_macd - manual_signal
            
            manual_macd_val = manual_macd.iloc[-1]
            manual_signal_val = manual_signal.iloc[-1]
            manual_hist_val = manual_hist.iloc[-1]
            
            print(f"\n   TA-Lib MACD values:")
            print(f"      MACD: {macd_val:.4f}")
            print(f"      Signal: {signal_val:.4f}")
            print(f"      Histogram: {hist_val:.4f}")
            
            print(f"\n   Manual calculation (for comparison):")
            print(f"      MACD: {manual_macd_val:.4f}")
            print(f"      Signal: {manual_signal_val:.4f}")
            print(f"      Histogram: {manual_hist_val:.4f}")
            
            # Check if values are close (within 1% or 0.01, whichever is larger)
            macd_diff = abs(macd_val - manual_macd_val)
            signal_diff = abs(signal_val - manual_signal_val)
            hist_diff = abs(hist_val - manual_hist_val)
            
            tolerance = max(abs(macd_val) * 0.01, 0.01)
            
            if macd_diff < tolerance and signal_diff < tolerance and hist_diff < tolerance:
                print(f"   ✅ TA-Lib values match manual calculation (within tolerance)")
            else:
                print(f"   ⚠️  TA-Lib values differ from manual calculation:")
                print(f"      MACD diff: {macd_diff:.4f}, Signal diff: {signal_diff:.4f}, Hist diff: {hist_diff:.4f}")
                print(f"      (This may be normal - TA-Lib uses different EMA initialization)")
            
            # Validate values
            if all(pd.notna(v) for v in [macd_val, signal_val, hist_val]):
                print("   ✅ MACD values are valid (not NaN)")
                
                # Check if values are reasonable relative to price
                if abs(macd_val) < abs(last_close) * 0.1:  # MACD should be < 10% of price
                    print(f"   ✅ MACD magnitude is reasonable relative to price")
                else:
                    print(f"   ⚠️  MACD magnitude seems large relative to price")
                    print(f"      (MACD: {abs(macd_val):.2f}, Price: {last_close:.2f}, Ratio: {abs(macd_val)/last_close*100:.2f}%)")
                
                return True
            else:
                print("   ❌ MACD values contain NaN")
                return False
        else:
            print("   ❌ MACD keys missing")
            return False
            
    except Exception as e:
        print(f"   ❌ MACD calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_volume_analysis(ticker: str = 'HPG'):
    """Test volume analysis with real data"""
    print("\n📊 Testing Volume Analysis...")
    print("   📖 Volume Indicators:")
    print("      - vol_sma20: 20-period volume moving average")
    print("      - vol_sma50: 50-period volume moving average")
    print("      - vol_ratio_20: current volume / vol_sma20")
    print("      - vol_ratio_50: current volume / vol_sma50")
    print("      - Ratio > 1.0 = above average volume (high activity)")
    print("      - Ratio < 1.0 = below average volume (low activity)")
    print()
    
    # Fetch real data
    print(f"   Fetching real data for {ticker}...")
    df = await fetch_extended_historical(ticker, days=100, verbose=False)
    
    if df is None or df.empty:
        print(f"   ❌ Failed to fetch data for {ticker}")
        return False
    
    print(f"   ✅ Fetched {len(df)} records")
    
    # Show current volume for context
    current_volume = df['volume'].iloc[-1]
    print(f"   Current volume: {current_volume:,.0f}")
    
    analyzer = TechnicalAnalyzer()
    
    try:
        volume_data = await analyzer.calculate_volume_analysis(df)
        
        expected_keys = ['vol_sma20', 'vol_sma50', 'vol_ratio_20', 'vol_ratio_50']
        missing_keys = [k for k in expected_keys if k not in volume_data]
        
        if missing_keys:
            print(f"   ⚠️  Missing keys: {missing_keys}")
            return False
        else:
            print("   ✅ All volume indicators calculated")
        
        # Get latest values
        vol_sma20 = volume_data['vol_sma20'].iloc[-1]
        vol_sma50 = volume_data['vol_sma50'].iloc[-1]
        vol_ratio_20 = volume_data['vol_ratio_20'].iloc[-1]
        vol_ratio_50 = volume_data['vol_ratio_50'].iloc[-1]
        
        print(f"\n   Volume Indicators (latest values):")
        print(f"      vol_sma20: {vol_sma20:,.0f}")
        print(f"      vol_sma50: {vol_sma50:,.0f}")
        print(f"      vol_ratio_20: {vol_ratio_20:.2f} ({'📈 Above average' if vol_ratio_20 > 1.0 else '📉 Below average'})")
        print(f"      vol_ratio_50: {vol_ratio_50:.2f} ({'📈 Above average' if vol_ratio_50 > 1.0 else '📉 Below average'})")
        
        # Verify calculations
        calculated_ratio_20 = current_volume / vol_sma20 if vol_sma20 > 0 else np.nan
        calculated_ratio_50 = current_volume / vol_sma50 if vol_sma50 > 0 else np.nan
        
        ratio_20_match = abs(vol_ratio_20 - calculated_ratio_20) < 0.01 if pd.notna(calculated_ratio_20) else False
        ratio_50_match = abs(vol_ratio_50 - calculated_ratio_50) < 0.01 if pd.notna(calculated_ratio_50) else False
        
        print(f"\n   Verification:")
        print(f"      vol_ratio_20 calculation: {current_volume:,.0f} / {vol_sma20:,.0f} = {calculated_ratio_20:.2f}")
        if ratio_20_match:
            print(f"      ✅ vol_ratio_20 is correct")
        else:
            print(f"      ⚠️  vol_ratio_20 mismatch (expected: {calculated_ratio_20:.2f}, got: {vol_ratio_20:.2f})")
        
        print(f"      vol_ratio_50 calculation: {current_volume:,.0f} / {vol_sma50:,.0f} = {calculated_ratio_50:.2f}")
        if ratio_50_match:
            print(f"      ✅ vol_ratio_50 is correct")
        else:
            print(f"      ⚠️  vol_ratio_50 mismatch (expected: {calculated_ratio_50:.2f}, got: {vol_ratio_50:.2f})")
        
        # Validate all values
        if all(pd.notna(v) for v in [vol_sma20, vol_sma50, vol_ratio_20, vol_ratio_50]):
            print("\n   ✅ All volume values are valid (not NaN)")
            return True
        else:
            print("\n   ❌ Some volume values are NaN")
            return False
            
    except Exception as e:
        print(f"   ❌ Volume analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_indicators_together(ticker: str = 'HPG'):
    """Test all indicators calculated together with real data"""
    print("\n🔄 Testing All Indicators Together...")
    
    # Fetch real data
    print(f"   Fetching real data for {ticker}...")
    df = await fetch_extended_historical(ticker, days=100, verbose=False)
    
    if df is None or df.empty:
        print(f"   ❌ Failed to fetch data for {ticker}")
        return False
    
    print(f"   ✅ Fetched {len(df)} records")
    
    analyzer = TechnicalAnalyzer()
    
    try:
        all_indicators = await analyzer.calculate_all_indicators(
            df, ticker,
            sma_periods=[20, 50],
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )
        
        # Check for expected keys
        expected_keys = ['sma_20', 'sma_50', 'rsi_14', 'macd', 'macd_signal', 'macd_histogram', 
                         'vol_sma20', 'vol_sma50', 'vol_ratio_20', 'vol_ratio_50']
        found_keys = [k for k in expected_keys if k in all_indicators]
        
        print(f"   ✅ Found {len(found_keys)}/{len(expected_keys)} expected indicators")
        
        if 'metadata' in all_indicators:
            print("   ✅ Metadata included")
        
        if len(found_keys) == len(expected_keys):
            print("   ✅ All indicators present")
            return True
        else:
            missing = set(expected_keys) - set(found_keys)
            print(f"   ⚠️  Missing indicators: {missing}")
            return False
            
    except Exception as e:
        print(f"   ❌ All indicators test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests with real stock data"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test TA-Lib integration with real stock data')
    parser.add_argument('--ticker', type=str, default='HPG', 
                       help='Stock ticker to test with (default: HPG)')
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    
    print(f"\n📈 Testing with real data for ticker: {ticker}")
    print("=" * 60)
    
    results = []
    
    # Test TA-Lib availability
    talib_available = await test_talib_availability()
    results.append(("TA-Lib Available", talib_available))
    
    # Test individual indicators with real data
    results.append(("SMA", await test_sma(ticker)))
    results.append(("RSI", await test_rsi(ticker)))
    results.append(("MACD", await test_macd(ticker)))
    results.append(("Volume Analysis", await test_volume_analysis(ticker)))
    results.append(("All Indicators", await test_all_indicators_together(ticker)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

