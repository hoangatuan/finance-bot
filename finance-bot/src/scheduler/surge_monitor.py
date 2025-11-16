"""
Scheduled Surge Monitoring Service
Monitors tickers for volume and price surges during trading hours
"""
import os
import asyncio
from datetime import datetime, time
from typing import List, Dict, Optional, Set

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    from backports.zoneinfo import ZoneInfo

try:
    from ..indicators.surge_detector import SurgeDetector
    from ..utils.ta_utils import run_technical_analysis
    from ..utils.data_fetcher import fetch_extended_historical
    from ..flow import analyze_ticker_multi_timeframe
    from ..notify.lark import LarkNotifier
except ImportError:
    from indicators.surge_detector import SurgeDetector
    from utils.ta_utils import run_technical_analysis
    from utils.data_fetcher import fetch_extended_historical
    from flow import analyze_ticker_multi_timeframe
    from notify.lark import LarkNotifier


class SurgeMonitor:
    """
    Monitors tickers for surges during trading hours
    """
    
    # Vietnam timezone (GMT+7)
    TZ_VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")
    
    # Trading hours (Vietnam time, GMT+7)
    # Adjusted by -1 hour for UTC+8 timezone
    TRADING_SESSION_1_START = time(8, 0)   # 8:00 AM (9:00 AM UTC+7)
    TRADING_SESSION_1_END = time(10, 30)     # 10:30 AM (11:30 AM UTC+7)
    TRADING_SESSION_2_START = time(12, 0)    # 12:00 PM (1:00 PM UTC+7)
    TRADING_SESSION_2_END = time(13, 45)     # 1:45 PM (2:45 PM UTC+7)
    
    def __init__(
        self,
        tickers: List[str],
        volume_multiplier: float = 1.5,
        price_change_pct: float = 3.0,
        lark_notifier: Optional[LarkNotifier] = None
    ):
        """
        Initialize surge monitor
        
        Args:
            tickers: List of ticker symbols to monitor
            volume_multiplier: Volume surge threshold
            price_change_pct: Price surge threshold
            lark_notifier: LarkNotifier instance (creates new one if not provided)
        """
        self.tickers = tickers
        self.surge_detector = SurgeDetector(
            volume_multiplier=volume_multiplier,
            price_change_pct=price_change_pct
        )
        self.lark_notifier = lark_notifier or LarkNotifier()
        self.last_surge_timestamps: Dict[str, datetime] = {}
    
    def check_trading_hours(self) -> bool:
        """
        Check if current time is within trading hours
        
        Returns:
            True if within trading hours (Mon-Fri, 9am-11:30am or 1pm-2:45pm)
        """
        now = datetime.now(self.TZ_VIETNAM)
        current_time = now.time()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Check if weekday (Mon-Fri)
        if weekday >= 5:  # Saturday or Sunday
            return False
        
        # Check if within trading session 1 (9am-11:30am)
        if self.TRADING_SESSION_1_START <= current_time <= self.TRADING_SESSION_1_END:
            return True
        
        # Check if within trading session 2 (1pm-2:45pm)
        if self.TRADING_SESSION_2_START <= current_time <= self.TRADING_SESSION_2_END:
            return True
        
        return False
    
    async def analyze_ticker(
        self,
        ticker: str,
        perform_deep_analysis: bool = True,
        force_analysis: bool = False
    ) -> Optional[Dict]:
        """
        Analyze a single ticker for surges
        
        Args:
            ticker: Stock ticker symbol
            perform_deep_analysis: If True, perform full multi-timeframe analysis when surge detected
        
        Returns:
            Dictionary with analysis results, or None if no surge detected
        """
        try:
            # Fetch recent data (last 60 days for daily data - need at least 50 for vol_ratio_50)
            # Use existing fetch_extended_historical function
            historical_df = await fetch_extended_historical(
                ticker=ticker,
                days=60,
                verbose=False
            )
            
            if historical_df is None or historical_df.empty:
                print(f"⚠️  No data available for {ticker}")
                return None
            
            # Use existing run_technical_analysis function
            processed_df = await run_technical_analysis(historical_df, ticker)
            
            if processed_df is None or processed_df.empty:
                print(f"⚠️  Failed to process data for {ticker}")
                return None
            
            # Detect surge
            surge_result = await self.surge_detector.detect_surge(processed_df)
            
            # If force_analysis is True, proceed even without surge (for testing)
            if not surge_result.get('has_surge') and not force_analysis:
                return None
            
            # Check if we've already notified for this surge (within last 30 minutes)
            last_surge_time = self.last_surge_timestamps.get(ticker)
            if last_surge_time:
                time_since_last = datetime.now() - last_surge_time
                if time_since_last.total_seconds() < 1800:  # 30 minutes
                    print(f"⏭️  Skipping {ticker} - surge already notified recently")
                    return None
            
            # Perform deep analysis if requested
            analysis_data = None
            if perform_deep_analysis:
                try:
                    print(f"🔍 Performing deep analysis for {ticker}...")
                    analysis_data = await analyze_ticker_multi_timeframe(
                        ticker=ticker,
                        verbose=False
                    )
                except Exception as e:
                    print(f"⚠️  Error in deep analysis for {ticker}: {e}")
                    analysis_data = None
            
            # Update last surge timestamp
            self.last_surge_timestamps[ticker] = datetime.now()
            
            return {
                'ticker': ticker,
                'surge_result': surge_result,
                'analysis_data': analysis_data,
                'processed_df': processed_df,  # Include processed data for volume ratios
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def monitor_tickers(
        self,
        perform_deep_analysis: bool = True,
        max_concurrent: int = 5,
        force_analysis: bool = False
    ) -> Dict[str, Dict]:
        """
        Monitor all tickers for surges
        
        Args:
            perform_deep_analysis: If True, perform full analysis when surge detected
            max_concurrent: Maximum number of tickers to analyze concurrently
        
        Returns:
            Dictionary mapping ticker to analysis results
        """
        results = {}
        
        # Process tickers with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(ticker: str):
            async with semaphore:
                return await self.analyze_ticker(ticker, perform_deep_analysis, force_analysis)
        
        # Create tasks for all tickers
        tasks = [analyze_with_semaphore(ticker) for ticker in self.tickers]
        
        # Execute all tasks
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(analysis_results):
            ticker = self.tickers[i]
            
            if isinstance(result, Exception):
                print(f"❌ Exception for {ticker}: {result}")
                results[ticker] = {'error': str(result)}
            elif result is not None:
                results[ticker] = result
                
                # Send notification if surge detected
                if self.lark_notifier:
                    try:
                        await self.lark_notifier.send_analysis(
                            ticker=ticker,
                            surge_data=result['surge_result'],
                            analysis_data=result.get('analysis_data'),
                            processed_df=result.get('processed_df')
                        )
                        print(f"✅ Sent Lark notification for {ticker}")
                    except Exception as e:
                        # Get the actual error message from the exception
                        error_msg = str(e)
                        if hasattr(e, '__cause__') and e.__cause__:
                            error_msg = str(e.__cause__)
                        print(f"❌ Failed to send notification for {ticker}: {error_msg}")
                        import traceback
                        print(f"   Error details: {traceback.format_exc()}")
                else:
                    print(f"⚠️  Lark notifier not configured, skipping notification for {ticker}")
        
        return results
    
    async def run_monitoring_cycle(
        self,
        perform_deep_analysis: bool = True,
        ignore_trading_hours: bool = False,
        force_analysis: bool = False
    ) -> Dict:
        """
        Run one complete monitoring cycle
        
        Args:
            perform_deep_analysis: If True, perform full analysis when surge detected
            ignore_trading_hours: If True, run even outside trading hours (for testing)
            force_analysis: If True, analyze all tickers even without surge (for testing)
        
        Returns:
            Dictionary with monitoring results
        """
        # Check trading hours (unless ignored for testing)
        if not ignore_trading_hours and not self.check_trading_hours():
            current_time = datetime.now(self.TZ_VIETNAM)
            return {
                'success': False,
                'reason': 'outside_trading_hours',
                'current_time': current_time.isoformat(),
                'message': f'Current time {current_time.strftime("%H:%M")} is outside trading hours'
            }
        
        if ignore_trading_hours:
            print(f"🧪 TEST MODE: Ignoring trading hours check")
        if force_analysis:
            print(f"🧪 TEST MODE: Forcing analysis for all tickers (even without surge)")
        
        print(f"🚀 Starting surge monitoring cycle at {datetime.now(self.TZ_VIETNAM).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Monitoring {len(self.tickers)} tickers: {', '.join(self.tickers)}")
        
        # Monitor all tickers
        results = await self.monitor_tickers(
            perform_deep_analysis=perform_deep_analysis,
            force_analysis=force_analysis
        )
        
        # Count surges detected
        surges_detected = sum(1 for r in results.values() if r.get('surge_result', {}).get('has_surge'))
        
        return {
            'success': True,
            'timestamp': datetime.now(self.TZ_VIETNAM).isoformat(),
            'tickers_monitored': len(self.tickers),
            'surges_detected': surges_detected,
            'results': results
        }

