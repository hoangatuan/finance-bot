#!/usr/bin/env python3
"""
Local Surge Monitor Runner
Runs surge monitoring every 30 minutes during trading hours
"""
import asyncio
import sys
import os
from datetime import datetime
import time
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from finance-bot directory
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try loading from current directory
        load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from scheduler.main import run_monitoring
    from scheduler.surge_monitor import SurgeMonitor
    from config.surge_config import SurgeConfig
except ImportError:
    # Fallback for direct execution
    from src.scheduler.main import run_monitoring
    from src.scheduler.surge_monitor import SurgeMonitor
    from src.config.surge_config import SurgeConfig


async def run_single_cycle(ignore_trading_hours=False, force_analysis=False):
    """Run a single monitoring cycle"""
    print(f"\n{'='*70}")
    print(f"🔄 Starting monitoring cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    result = await run_monitoring(
        config_path=None,
        perform_deep_analysis=True,
        verbose=True,
        ignore_trading_hours=ignore_trading_hours,
        force_analysis=force_analysis
    )
    
    print(f"\n{'='*70}")
    if result.get('success'):
        print(f"✅ Cycle completed: {result.get('surges_detected', 0)} surge(s) detected")
    else:
        print(f"⏭️  Cycle skipped: {result.get('reason', 'unknown')}")
    print(f"{'='*70}\n")
    
    return result


async def run_continuous():
    """
    Run monitoring continuously, checking every 30 minutes
    Only runs during trading hours (9am-11:30am and 1pm-2:45pm, Mon-Fri)
    """
    print("🚀 Starting continuous surge monitoring service")
    print("   Monitoring every 30 minutes during trading hours")
    print("   Press Ctrl+C to stop\n")
    
    # Load config to get monitor instance for trading hours check
    config = SurgeConfig()
    tickers = config.get_tickers()
    
    if not tickers:
        print("❌ No tickers configured. Exiting.")
        return
    
    monitor = SurgeMonitor(
        tickers=tickers,
        volume_multiplier=config.get_volume_multiplier(),
        price_change_pct=config.get_price_change_pct(),
        lark_notifier=config.get_lark_notifier()
    )
    
    cycle_count = 0
    
    try:
        while True:
            # Check if we're in trading hours
            if monitor.check_trading_hours():
                cycle_count += 1
                print(f"\n📊 Cycle #{cycle_count}")
                result = await run_single_cycle()
            else:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"⏸️  Outside trading hours ({current_time}). Waiting...")
            
            # Wait 30 minutes (1800 seconds) before next check
            print("⏳ Waiting 30 minutes until next check...\n")
            await asyncio.sleep(1800)  # 30 minutes
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring service stopped by user")
        print(f"   Completed {cycle_count} monitoring cycles")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Surge Monitoring Service')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run a single monitoring cycle and exit'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to monitored_tickers.yaml config file'
    )
    parser.add_argument(
        '--no-deep-analysis',
        action='store_true',
        help='Skip deep analysis when surge detected'
    )
    parser.add_argument(
        '--ignore-trading-hours',
        action='store_true',
        help='Run even outside trading hours (for testing)'
    )
    parser.add_argument(
        '--force-analysis',
        action='store_true',
        help='Force analysis for all tickers even without surge (for testing)'
    )
    
    args = parser.parse_args()
    
    if args.once:
        # Run once and exit
        result = await run_monitoring(
            config_path=args.config,
            perform_deep_analysis=not args.no_deep_analysis,
            verbose=True,
            ignore_trading_hours=args.ignore_trading_hours,
            force_analysis=args.force_analysis
        )
        sys.exit(0 if result.get('success') or result.get('reason') == 'outside_trading_hours' else 1)
    else:
        # Run continuously
        await run_continuous()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

