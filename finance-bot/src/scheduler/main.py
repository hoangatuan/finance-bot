"""
Main Entry Point for Scheduled Surge Monitoring
"""
import asyncio
import sys
import os
from typing import Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to find .env file in finance-bot directory
    base_dir = Path(__file__).parent.parent.parent
    env_path = base_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try loading from current directory
        load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from scheduler.surge_monitor import SurgeMonitor
    from config.surge_config import SurgeConfig
except ImportError:
    from src.scheduler.surge_monitor import SurgeMonitor
    from src.config.surge_config import SurgeConfig


async def run_monitoring(
    config_path: Optional[str] = None,
    perform_deep_analysis: bool = True,
    verbose: bool = True,
    ignore_trading_hours: bool = False,
    force_analysis: bool = False
) -> dict:
    """
    Run one monitoring cycle
    
    Args:
        config_path: Path to monitored_tickers.yaml config file
        perform_deep_analysis: If True, perform full multi-timeframe analysis when surge detected
        verbose: If True, print progress messages
    
    Returns:
        Dictionary with monitoring results
    """
    # Load configuration
    config = SurgeConfig(config_path)
    
    # Get tickers and thresholds
    tickers = config.get_tickers()
    volume_multiplier = config.get_volume_multiplier()
    price_change_pct = config.get_price_change_pct()
    
    if not tickers:
        error_msg = "No tickers configured. Please set MONITORED_TICKERS environment variable or configure monitored_tickers.yaml"
        if verbose:
            print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    
    if verbose:
        print(f"📋 Configuration:")
        print(f"   Tickers: {', '.join(tickers)}")
        print(f"   Volume Threshold: {volume_multiplier}x")
        print(f"   Price Threshold: {price_change_pct}%")
    
    # Get Lark notifier
    lark_notifier = config.get_lark_notifier()
    if not lark_notifier:
        if verbose:
            print("⚠️  Lark credentials not configured. Notifications will be skipped.")
    
    # Create monitor
    monitor = SurgeMonitor(
        tickers=tickers,
        volume_multiplier=volume_multiplier,
        price_change_pct=price_change_pct,
        lark_notifier=lark_notifier
    )
    
    # Run monitoring cycle
    result = await monitor.run_monitoring_cycle(
        perform_deep_analysis=perform_deep_analysis,
        ignore_trading_hours=ignore_trading_hours,
        force_analysis=force_analysis
    )
    
    if verbose:
        if result.get('success'):
            print(f"\n✅ Monitoring cycle completed")
            print(f"   Surges detected: {result.get('surges_detected', 0)}")
        else:
            print(f"\n⚠️  Monitoring cycle skipped: {result.get('reason', 'unknown')}")
            print(f"   {result.get('message', '')}")
    
    return result


async def main():
    """
    Main entry point for CLI execution
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Surge Monitoring Service')
    parser.add_argument(
        '--config',
        type=str,
        help='Path to monitored_tickers.yaml config file'
    )
    parser.add_argument(
        '--no-deep-analysis',
        action='store_true',
        help='Skip deep analysis when surge detected (faster but less detailed)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
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
    
    # Run monitoring
    result = await run_monitoring(
        config_path=args.config,
        perform_deep_analysis=not args.no_deep_analysis,
        verbose=not args.quiet,
        ignore_trading_hours=args.ignore_trading_hours,
        force_analysis=args.force_analysis
    )
    
    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    asyncio.run(main())

