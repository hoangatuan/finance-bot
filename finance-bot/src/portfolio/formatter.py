"""
Portfolio Formatter - Format portfolio analysis output
"""
from typing import Dict, List, Any, Optional
from datetime import datetime


def format_portfolio_analysis(analysis_result: Dict[str, Any], 
                             ai_advice: Optional[Dict[str, Any]] = None) -> str:
    """
    Format portfolio analysis results and AI advice into human-readable output
    
    Args:
        analysis_result: Dictionary from run_daily_analysis() with portfolio, ta_results, portfolio_summary
        ai_advice: Optional dictionary from AI analyzer with portfolio advice
        
    Returns:
        Formatted string for display
    """
    lines = []
    
    portfolio = analysis_result.get("portfolio", {})
    ta_results = analysis_result.get("ta_results", {})
    portfolio_summary = analysis_result.get("portfolio_summary", {})
    cash_balance = portfolio.get("cash_balance", {})
    
    # Header
    lines.append("\n" + "=" * 80)
    lines.append("📊 PORTFOLIO ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append(f"Analysis Date: {portfolio_summary.get('analysis_timestamp', 'N/A')}")
    
    # Portfolio Summary
    lines.append("\n" + "-" * 80)
    lines.append("💰 PORTFOLIO SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total Positions: {portfolio_summary.get('total_positions', 0)}")
    lines.append(f"Cash Balance: {cash_balance.get('balance', 0):,.0f} {cash_balance.get('currency', 'VND')}")
    lines.append(f"Total Portfolio Value: {portfolio_summary.get('total_value', 0):,.0f} VND")
    lines.append(f"Total Cost Basis: {portfolio_summary.get('total_cost', 0):,.0f} VND")
    
    total_pnl = portfolio_summary.get('total_pnl', 0)
    total_pnl_pct = portfolio_summary.get('total_pnl_pct', 0)
    pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
    lines.append(f"{pnl_emoji} Total P&L: {total_pnl:,.0f} VND ({total_pnl_pct:+.2f}%)")
    
    # Individual Stock Analysis
    if ta_results:
        lines.append("\n" + "-" * 80)
        lines.append("📈 INDIVIDUAL STOCK ANALYSIS")
        lines.append("-" * 80)
        
        for symbol, ta_result in sorted(ta_results.items()):
            if "error" in ta_result:
                lines.append(f"\n❌ {symbol}: {ta_result['error']}")
                continue
            
            stock = ta_result.get("stock", {})
            current_price = ta_result.get("current_price", 0)
            indicators = ta_result.get("indicators", {})
            position_pnl = ta_result.get("position_pnl", 0)
            position_pnl_pct = ta_result.get("position_pnl_pct", 0)
            
            lines.append(f"\n📊 {symbol}")
            lines.append(f"   Position: {stock.get('total_shares', 0):,} shares")
            lines.append(f"   Avg Buy Price: {stock.get('avg_buy_price', 0):,.2f} VND")
            # current_price is in full VND format
            lines.append(f"   Current Price: {current_price:,.2f} VND")
            lines.append(f"   Position Value: {ta_result.get('position_value', 0):,.0f} VND")
            
            pnl_emoji_stock = "🟢" if position_pnl >= 0 else "🔴"
            lines.append(f"   {pnl_emoji_stock} P&L: {position_pnl:,.0f} VND ({position_pnl_pct:+.2f}%)")
            
            if stock.get('sector'):
                lines.append(f"   Sector: {stock.get('sector')}")
            
            # Technical Indicators Summary
            lines.append(f"\n   Technical Indicators:")
            if indicators.get('sma_20') is not None:
                lines.append(f"      SMA(20): {indicators.get('sma_20', 0):,.2f}")
            if indicators.get('sma_50') is not None:
                lines.append(f"      SMA(50): {indicators.get('sma_50', 0):,.2f}")
            if indicators.get('rsi_14') is not None:
                rsi = indicators.get('rsi_14', 50)
                rsi_status = "🔴 Oversold" if rsi < 30 else "🟡 Overbought" if rsi > 70 else "🟢 Neutral"
                lines.append(f"      RSI(14): {rsi:.2f} {rsi_status}")
            if indicators.get('macd') is not None:
                macd = indicators.get('macd', 0)
                macd_signal = indicators.get('macd_signal', 0)
                macd_status = "🟢 Bullish" if macd > macd_signal else "🔴 Bearish"
                lines.append(f"      MACD: {macd:.2f} (Signal: {macd_signal:.2f}) {macd_status}")
            if indicators.get('volume_ratio') is not None:
                vol_ratio = indicators.get('volume_ratio', 1.0)
                vol_status = "📈 High" if vol_ratio > 1.5 else "📉 Low" if vol_ratio < 0.5 else "➡️ Normal"
                lines.append(f"      Volume Ratio: {vol_ratio:.2f} {vol_status}")
            
            # Support/Resistance Summary
            # Zones are now in full VND format (converted in analyzer)
            zones = ta_result.get("support_resistance", {})
            if zones:
                if zones.get('support_zones'):
                    nearest_sup = zones['support_zones'][0] if zones['support_zones'] else None
                    if nearest_sup:
                        # Zones are in full VND format
                        support_middle = nearest_sup.get('middle', 0)
                        support_distance = nearest_sup.get('distance_pct', 0)
                        direction = "below" if support_distance < 0 else "above"
                        lines.append(f"\n   🛡️  Nearest Support: {support_middle:,.2f} VND")
                        lines.append(f"      (Distance: {abs(support_distance):.2f}% {direction}, Strength: {nearest_sup.get('strength', 0):.2f})")
                
                if zones.get('resistance_zones'):
                    nearest_res = zones['resistance_zones'][0] if zones['resistance_zones'] else None
                    if nearest_res:
                        # Zones are in full VND format
                        resistance_middle = nearest_res.get('middle', 0)
                        resistance_distance = nearest_res.get('distance_pct', 0)
                        direction = "above" if resistance_distance > 0 else "below"
                        lines.append(f"\n   ⚡ Nearest Resistance: {resistance_middle:,.2f} VND")
                        lines.append(f"      (Distance: {abs(resistance_distance):.2f}% {direction}, Strength: {nearest_res.get('strength', 0):.2f})")
    
    # AI Advice Section
    if ai_advice:
        lines.append("\n" + "-" * 80)
        lines.append("🤖 AI PORTFOLIO ADVICE")
        lines.append("-" * 80)
        
        if "error" in ai_advice:
            lines.append(f"\n❌ Error getting AI advice: {ai_advice['error']}")
        elif ai_advice.get("raw_response"):
            # Format the AI response
            ai_response = ai_advice["raw_response"]
            
            # Split into lines and add indentation for better readability
            response_lines = ai_response.split('\n')
            for line in response_lines:
                if line.strip():
                    # Add indentation for body text, keep headers as-is
                    if line.strip().startswith('##') or line.strip().startswith('#'):
                        lines.append(f"\n{line}")
                    elif line.strip().startswith('-') or line.strip().startswith('•') or line.strip().startswith('*'):
                        lines.append(f"   {line}")
                    elif line.strip() and not line.strip().startswith('**'):
                        lines.append(f"   {line}")
                    else:
                        lines.append(line)
            
            lines.append(f"\n   (Generated by {ai_advice.get('model_used', 'AI')})")
        else:
            lines.append("\n⚠️  No AI advice available")
    else:
        lines.append("\n" + "-" * 80)
        lines.append("⚠️  AI Advice: Not requested or unavailable")
        lines.append("-" * 80)
    
    # Footer
    lines.append("\n" + "=" * 80)
    lines.append("End of Report")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def format_portfolio_summary_only(portfolio_summary: Dict[str, Any]) -> str:
    """
    Format just the portfolio summary without detailed analysis
    
    Args:
        portfolio_summary: Portfolio summary dictionary
        
    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("💰 PORTFOLIO SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Total Positions: {portfolio_summary.get('total_positions', 0)}")
    lines.append(f"Total Portfolio Value: {portfolio_summary.get('total_value', 0):,.0f} VND")
    lines.append(f"Total Cost Basis: {portfolio_summary.get('total_cost', 0):,.0f} VND")
    
    total_pnl = portfolio_summary.get('total_pnl', 0)
    total_pnl_pct = portfolio_summary.get('total_pnl_pct', 0)
    pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
    lines.append(f"{pnl_emoji} Total P&L: {total_pnl:,.0f} VND ({total_pnl_pct:+.2f}%)")
    lines.append("=" * 70)
    
    return "\n".join(lines)

