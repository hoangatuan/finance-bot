#!/usr/bin/env python3
"""
Test script for VNStock fetcher
"""
import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fetcher.fetcher_factory import FetcherFactory
from fetcher.vnstock_fetcher import VNStockFetcher


async def test_historical_fetch():
    """Test historical data fetching"""
    print("Testing Historical Data Fetch...")
    
    try:
        # Create fetcher
        fetcher = VNStockFetcher(rate_limit=60, default_source='VCI')
        
        # Test historical data with VCI source
        print("Fetching VNM historical data from VCI (last 30 days)...")
        data = await fetcher.fetch_historical(
            ticker='VNM',
            start_date='2024-01-01',
            end_date='2024-01-31',
            interval='1D',
            source='VCI'
        )
        
        if not data.empty:
            print(f"✅ Successfully fetched {len(data)} records from VCI")
            print(f"Columns: {list(data.columns)}")
            print(f"First row: {data.iloc[0].to_dict()}")
            print(f"Last row: {data.iloc[-1].to_dict()}")
        else:
            print("❌ No data returned from VCI")
            
    except Exception as e:
        print(f"❌ Error testing historical fetch: {e}")


async def test_multiple_sources():
    """Test fetching from multiple sources"""
    print("\nTesting Multiple Sources Fetch...")
    
    try:
        fetcher = VNStockFetcher(rate_limit=60)
        
        print("Trying to fetch VNM data from multiple sources...")
        data = await fetcher.fetch_from_multiple_sources(
            ticker='VNM',
            start_date='2024-01-01',
            end_date='2024-01-31',
            interval='1D'
        )
        
        if not data.empty:
            print(f"✅ Successfully fetched data from multiple sources")
            print(f"Source used: {data['source_detail'].iloc[0]}")
            print(f"Records: {len(data)}")
        else:
            print("❌ No data returned from any source")
            
    except Exception as e:
        print(f"❌ Error testing multiple sources: {e}")


async def test_realtime_fetch():
    """Test real-time data fetching"""
    print("\nTesting Real-time Data Fetch...")
    
    try:
        # Create fetcher
        fetcher = VNStockFetcher(rate_limit=60)
        
        # Test real-time data
        print("Fetching real-time data for VNM, HPG...")
        realtime_data = await fetcher.fetch_realtime(['VNM', 'HPG'])
        
        if realtime_data:
            print(f"✅ Successfully fetched {len(realtime_data)} real-time records")
            for data in realtime_data:
                print(f"  {data.ticker}: Close={data.close}, Volume={data.volume}")
        else:
            print("❌ No real-time data returned")
            
    except Exception as e:
        print(f"❌ Error testing real-time fetch: {e}")


async def test_factory():
    """Test fetcher factory"""
    print("\nTesting Fetcher Factory...")
    
    try:
        # Test factory creation
        fetcher = FetcherFactory.create_fetcher('vnstock', rate_limit=60, default_source='TCBS')
        print(f"✅ Successfully created fetcher: {type(fetcher).__name__}")
        print(f"Default source: {fetcher.default_source}")
        
        # Test supported sources
        sources = FetcherFactory.get_supported_sources()
        print(f"✅ Supported sources: {sources}")
        
    except Exception as e:
        print(f"❌ Error testing factory: {e}")


async def test_trading_status():
    """Test trading status check"""
    print("\nTesting Trading Status...")
    
    try:
        fetcher = VNStockFetcher()
        status = fetcher.get_trading_status()
        
        print(f"✅ Trading status: {status}")
        
    except Exception as e:
        print(f"❌ Error testing trading status: {e}")


async def test_interval_validation():
    """Test interval validation"""
    print("\nTesting Interval Validation...")
    
    try:
        fetcher = VNStockFetcher()
        
        # Test valid intervals
        valid_intervals = ['1m', '5m', '15m', '30m', '1H', '1D', '1W', '1M']
        for interval in valid_intervals:
            is_valid = fetcher.validate_interval(interval)
            print(f"  {interval}: {'✅' if is_valid else '❌'}")
        
        # Test invalid interval
        is_valid = fetcher.validate_interval('2H')
        print(f"  2H: {'✅' if is_valid else '❌'}")
        
        # Test interval to minutes conversion
        print(f"\nInterval to minutes conversion:")
        for interval in ['5m', '1H', '1D']:
            minutes = fetcher.get_interval_minutes(interval)
            print(f"  {interval} = {minutes} minutes")
            
    except Exception as e:
        print(f"❌ Error testing interval validation: {e}")


async def main():
    """Main test function"""
    print("🚀 Starting VNStock Fetcher Tests...\n")
    
    # Run tests
    await test_factory()
    await test_interval_validation()
    await test_historical_fetch()
    await test_multiple_sources()
    await test_realtime_fetch()
    await test_trading_status()
    
    print("\n✨ All tests completed!")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(main())
