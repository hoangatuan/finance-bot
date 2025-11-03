"""
Portfolio Analyzer - Daily analysis routine for portfolio stocks
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from store.portfolio_manager import PortfolioManager
    from indicators.pipeline import IndicatorPipeline
    from indicators.support_resistance import SupportResistanceAnalyzer
    from utils.data_fetcher import fetch_extended_historical, get_current_price
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.store.portfolio_manager import PortfolioManager
    from src.indicators.pipeline import IndicatorPipeline
    from src.indicators.support_resistance import SupportResistanceAnalyzer
    from src.utils.data_fetcher import fetch_extended_historical, get_current_price


async def run_daily_analysis(
    portfolio_path: Optional[str] = None,
    days_history: int = 250,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run daily technical analysis on all portfolio stocks
    
    This function:
    1. Loads portfolio from JSON
    2. For each stock: fetches data → runs TA → collects results
    3. Calculates current P&L for each position
    4. Returns structured data for AI analysis
    
    Args:
        portfolio_path: Path to portfolio JSON file. If None, uses default.
        days_history: Number of days of historical data to fetch (default 250)
        verbose: If True, print progress messages
        
    Returns:
        Dictionary with portfolio data, TA results, and calculated metrics
    """
    if verbose:
        print("\n" + "=" * 70)
        print("📊 Portfolio Daily Analysis")
        print("=" * 70)
    
    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(portfolio_path)
    
    # Load portfolio
    if verbose:
        print(f"\n📥 Loading portfolio from: {portfolio_manager.get_portfolio_file_path()}")
    
    portfolio = portfolio_manager.load_portfolio()
    
    if not portfolio.get("stocks"):
        if verbose:
            print("⚠️  Portfolio is empty. No stocks to analyze.")
        return {
            "portfolio": portfolio,
            "ta_results": {},
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    stocks = portfolio["stocks"]
    cash_balance = portfolio.get("cash_balance", {})
    
    if verbose:
        print(f"✅ Loaded portfolio with {len(stocks)} stocks")
        print(f"💰 Cash balance: {cash_balance.get('balance', 0):,.0f} {cash_balance.get('currency', 'VND')}")
    
    # Initialize TA pipeline
    pipeline = IndicatorPipeline()
    sr_analyzer = SupportResistanceAnalyzer()
    
    # Collect TA results for all stocks
    ta_results = {}
    portfolio_summary = {
        "total_positions": len(stocks),
        "total_value": 0.0,
        "total_cost": 0.0,
        "total_pnl": 0.0,
        "total_pnl_pct": 0.0
    }
    
    if verbose:
        print(f"\n🔬 Running Technical Analysis for {len(stocks)} stocks...")
    
    for idx, stock in enumerate(stocks, 1):
        symbol = stock["symbol"]
        
        if verbose:
            print(f"\n[{idx}/{len(stocks)}] Analyzing {symbol}...")
        
        try:
            # Fetch historical data
            if verbose:
                print(f"   📥 Fetching historical data...")
            
            historical_df = await fetch_extended_historical(
                symbol, 
                days=days_history,
                verbose=False
            )
            
            if historical_df is None or historical_df.empty:
                if verbose:
                    print(f"   ❌ Failed to fetch data for {symbol}")
                ta_results[symbol] = {
                    "error": "Failed to fetch historical data",
                    "stock": stock
                }
                continue
            
            # Get current price
            # Note: VNStock returns prices in thousands format (e.g., 26.05 = 26,050 VND)
            # Portfolio prices are stored in storage format (divided by 1000) in JSON,
            # but load_portfolio() converts them to full format (VND) for internal use.
            # So we need to ensure current_price is also in full format (VND) for calculations.
            historical_close = historical_df.iloc[-1]['close']
            current_price_raw = await get_current_price(symbol, historical_close, verbose=False)
            if current_price_raw is None:
                current_price_raw = historical_close
            
            # VNStock returns prices in thousands (e.g., 26.05 = 26,050 VND)
            # Convert to full VND format for consistency with portfolio prices
            # Check if price seems to be in thousands (< 1000) vs full format
            if current_price_raw < 1000:
                # Likely in thousands format, convert to full VND
                current_price = current_price_raw * 1000
            else:
                # Already in full VND format
                current_price = current_price_raw
            
            # Run technical analysis
            if verbose:
                print(f"   📈 Running technical analysis...")
            
            processed_df = await pipeline.process_historical_data(
                historical_df,
                symbol,
                sma_periods=[20, 50],
                rsi_period=14,
                macd_fast=12,
                macd_slow=26,
                macd_signal=9,
                volume_avg_period=20
            )
            
            if processed_df.empty:
                if verbose:
                    print(f"   ❌ Technical analysis failed for {symbol}")
                ta_results[symbol] = {
                    "error": "Technical analysis failed",
                    "stock": stock,
                    "current_price": current_price
                }
                continue
            
            # Get latest indicators
            latest_indicators = processed_df.iloc[-1].to_dict()
            
            # Analyze support and resistance
            # Note: Historical data and processed_df are in thousands format (e.g., 25.64 = 25,640 VND)
            # But current_price is now in full VND format. We need to convert it back to thousands
            # format for the support/resistance analyzer to work correctly.
            if verbose:
                print(f"   🛡️  Analyzing support & resistance...")
            
            # Convert current_price to thousands format for S/R analysis
            # (same format as historical_df and indicators)
            current_price_for_sr = current_price / 1000.0 if current_price >= 1000 else current_price
            
            zones = await sr_analyzer.find_pivots(processed_df, left_bars=5, right_bars=5)
            pivot_zones = await sr_analyzer.create_pivot_zones(
                zones,
                current_price_for_sr,  # Use thousands format for S/R analysis
                df=processed_df,
                tolerance_percent=1.5,
                min_touches=2,
                include_touching_levels=True
            )
            
            # Convert support/resistance zones back to full VND format for display/use
            # This ensures consistency with current_price and portfolio calculations
            if pivot_zones.get('support_zones'):
                for zone in pivot_zones['support_zones']:
                    zone['lower'] = zone.get('lower', 0) * 1000
                    zone['upper'] = zone.get('upper', 0) * 1000
                    zone['middle'] = zone.get('middle', 0) * 1000
                    # Recalculate distance_pct using full VND prices
                    if current_price > 0:
                        zone['distance_pct'] = ((zone['middle'] - current_price) / current_price) * 100
            
            if pivot_zones.get('resistance_zones'):
                for zone in pivot_zones['resistance_zones']:
                    zone['lower'] = zone.get('lower', 0) * 1000
                    zone['upper'] = zone.get('upper', 0) * 1000
                    zone['middle'] = zone.get('middle', 0) * 1000
                    # Recalculate distance_pct using full VND prices
                    if current_price > 0:
                        zone['distance_pct'] = ((zone['middle'] - current_price) / current_price) * 100
            
            # Calculate position metrics
            # avg_buy_price from portfolio is already in full format (converted by load_portfolio)
            # current_price is now also in full format (VND) after conversion above
            total_shares = stock.get("total_shares", 0)
            avg_buy_price = stock.get("avg_buy_price", 0)  # Already in full format (VND)
            
            position_value = total_shares * current_price
            position_cost = total_shares * avg_buy_price
            position_pnl = position_value - position_cost
            position_pnl_pct = (position_pnl / position_cost * 100) if position_cost > 0 else 0
            
            # Update portfolio summary
            portfolio_summary["total_value"] += position_value
            portfolio_summary["total_cost"] += position_cost
            portfolio_summary["total_pnl"] += position_pnl
            
            # Collect TA results
            ta_results[symbol] = {
                "stock": stock,
                "current_price": current_price,
                "position_value": position_value,
                "position_cost": position_cost,
                "position_pnl": position_pnl,
                "position_pnl_pct": position_pnl_pct,
                "indicators": {
                    "sma_20": latest_indicators.get("sma_20"),
                    "sma_50": latest_indicators.get("sma_50"),
                    "rsi_14": latest_indicators.get("rsi_14"),
                    "macd": latest_indicators.get("macd"),
                    "macd_signal": latest_indicators.get("macd_signal"),
                    "macd_hist": latest_indicators.get("macd_hist"),
                    "volume_ratio": latest_indicators.get("volume_ratio")
                },
                "support_resistance": pivot_zones,
                "historical_data": processed_df,
                "transaction_history": stock.get("transactions", [])
            }
            
            if verbose:
                print(f"   ✅ {symbol} analysis complete")
                print(f"      Current Price: {current_price:,.2f}")
                print(f"      Position Value: {position_value:,.0f}")
                print(f"      P&L: {position_pnl:,.0f} ({position_pnl_pct:+.2f}%)")
        
        except Exception as e:
            if verbose:
                print(f"   ❌ Error analyzing {symbol}: {e}")
                import traceback
                traceback.print_exc()
            ta_results[symbol] = {
                "error": str(e),
                "stock": stock
            }
    
    # Calculate total P&L percentage
    if portfolio_summary["total_cost"] > 0:
        portfolio_summary["total_pnl_pct"] = (
            portfolio_summary["total_pnl"] / portfolio_summary["total_cost"] * 100
        )
    
    if verbose:
        print(f"\n✅ Analysis complete!")
        print(f"   Total Positions: {portfolio_summary['total_positions']}")
        print(f"   Total Portfolio Value: {portfolio_summary['total_value']:,.0f}")
        print(f"   Total Cost: {portfolio_summary['total_cost']:,.0f}")
        print(f"   Total P&L: {portfolio_summary['total_pnl']:,.0f} ({portfolio_summary['total_pnl_pct']:+.2f}%)")
        print("=" * 70)
    
    return {
        "portfolio": portfolio,
        "ta_results": ta_results,
        "portfolio_summary": portfolio_summary,
        "analysis_timestamp": datetime.now().isoformat()
    }

