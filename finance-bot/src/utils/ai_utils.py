"""
AI Analysis utilities
"""
import os
import pandas as pd
from typing import Dict, Optional

try:
    from ..indicators.ai_analyzer import OpenAIAnalyzer
except ImportError:
    # Fallback for when running as script
    from indicators.ai_analyzer import OpenAIAnalyzer


async def get_ai_suggestions(
    ticker: str,
    current_price: float,
    indicators: Dict,
    zones: Dict,
    df: pd.DataFrame
) -> Optional[Dict]:
    """
    Get AI trading suggestions from OpenAI based on technical analysis
    
    Args:
        ticker: Stock symbol
        current_price: Current stock price
        indicators: Dictionary with latest indicator values
        zones: Dictionary with support/resistance zones
        df: DataFrame with historical data for recent price action
    
    Returns:
        Dictionary with AI suggestions or None if error/not configured
    """
    try:
        # Check if OpenAI API key is configured
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("\n⚠️  OpenAI API key not configured. Skipping AI suggestions.")
            print("   Set OPENAI_API_KEY environment variable to enable AI analysis.")
            return None
        
        print("\n🤖 Getting AI Trading Suggestions...")
        
        # Create AI analyzer
        ai_analyzer = OpenAIAnalyzer()
        
        # Get recent price action
        recent_price_action = None
        if not df.empty and len(df) >= 10:
            recent_price_action = {
                'high': df['high'].tail(10).max(),
                'low': df['low'].tail(10).min(),
                'trend': 'uptrend' if df['close'].iloc[-1] > df['close'].iloc[-10] else 'downtrend'
            }
        
        # Get AI suggestions (AI will analyze indicators directly)
        suggestions = await ai_analyzer.get_trading_suggestions(
            ticker=ticker,
            current_price=current_price,
            indicators=indicators,
            zones=zones,
            recent_price_action=recent_price_action
        )
        
        # Display formatted output
        if suggestions and 'error' not in suggestions:
            formatted_output = ai_analyzer.format_suggestions_output(suggestions)
            print(formatted_output)
        elif suggestions and 'error' in suggestions:
            print(f"❌ Error getting AI suggestions: {suggestions['error']}")
            return None
        else:
            print("❌ No suggestions returned from AI")
            return None
        
        return suggestions
        
    except ValueError as e:
        # API key not configured - this is okay, just skip
        print(f"\n⚠️  {str(e)}")
        return None
    except Exception as e:
        print(f"\n❌ Error getting AI suggestions: {e}")
        import traceback
        traceback.print_exc()
        return None

