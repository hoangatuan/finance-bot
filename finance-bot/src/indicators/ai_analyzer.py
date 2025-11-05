"""
OpenAI AI Analyzer for generating trading suggestions based on technical analysis
"""
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
import pandas as pd
from openai import OpenAI


class OpenAIAnalyzer:
    """Analyzer that uses OpenAI to generate trading suggestions from technical data"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI Analyzer
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var
            model: OpenAI model to use (default: gpt-3.5-turbo)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def format_technical_data(self, 
                             ticker: str,
                             current_price: float,
                             indicators: Dict,
                             zones: Dict,
                             signals: List[str],
                             recent_price_action: Optional[Dict] = None) -> str:
        """
        Format technical analysis data into a structured prompt for OpenAI
        
        Args:
            ticker: Stock symbol
            current_price: Current stock price
            indicators: Dictionary with latest indicator values
            zones: Dictionary with support/resistance zones
            signals: List of trading signals
            recent_price_action: Optional recent price action summary
        
        Returns:
            Formatted string with technical data
        """
        lines = [
            f"## Stock Analysis Request for {ticker}",
            f"\n**Current Price:** {current_price:,.2f} VND",
        ]
        
        # Technical Indicators
        lines.append("\n### Technical Indicators:")
        if pd.notna(indicators.get('sma_20')):
            lines.append(f"- SMA(20): {indicators['sma_20']:,.2f}")
        if pd.notna(indicators.get('sma_50')):
            lines.append(f"- SMA(50): {indicators['sma_50']:,.2f}")
        if pd.notna(indicators.get('rsi_14')):
            lines.append(f"- RSI(14): {indicators['rsi_14']:.2f}")
        if pd.notna(indicators.get('macd')):
            lines.append(f"- MACD: {indicators['macd']:.2f}")
        if pd.notna(indicators.get('macd_signal')):
            lines.append(f"- MACD Signal: {indicators['macd_signal']:.2f}")
        if pd.notna(indicators.get('volume_ratio')):
            lines.append(f"- Volume Ratio: {indicators['volume_ratio']:.2f}")
        
        # Support/Resistance Zones
        if zones:
            lines.append("\n### Support & Resistance Zones:")
            
            if zones.get('resistance_zones'):
                lines.append("\n**Resistance Zones (above current price):**")
                for i, zone in enumerate(zones['resistance_zones'][:3], 1):
                    lines.append(
                        f"{i}. Zone: {zone['lower']:,.2f} - {zone['upper']:,.2f} "
                        f"(Middle: {zone['middle']:,.2f}, Distance: {zone['distance_pct']:.2f}% above, "
                        f"Strength: {zone['strength']:.2f}, Touches: {zone['touch_count']})"
                    )
                    if 'confidence_score' in zone:
                        lines.append(f"   Confidence: {zone['confidence_score']:.2f} - {zone.get('interpretation', 'N/A')}")
            
            if zones.get('support_zones'):
                lines.append("\n**Support Zones (below current price):**")
                for i, zone in enumerate(zones['support_zones'][:3], 1):
                    lines.append(
                        f"{i}. Zone: {zone['lower']:,.2f} - {zone['upper']:,.2f} "
                        f"(Middle: {zone['middle']:,.2f}, Distance: {zone['distance_pct']:.2f}% below, "
                        f"Strength: {zone['strength']:.2f}, Touches: {zone['touch_count']})"
                    )
                    if 'confidence_score' in zone:
                        lines.append(f"   Confidence: {zone['confidence_score']:.2f} - {zone.get('interpretation', 'N/A')}")
        
        # Trading Signals
        if signals:
            lines.append("\n### Current Trading Signals:")
            for signal in signals:
                lines.append(f"- {signal}")
        
        # Recent Price Action
        if recent_price_action:
            lines.append("\n### Recent Price Action:")
            if 'high' in recent_price_action:
                lines.append(f"- Recent High: {recent_price_action['high']:,.2f}")
            if 'low' in recent_price_action:
                lines.append(f"- Recent Low: {recent_price_action['low']:,.2f}")
            if 'trend' in recent_price_action:
                lines.append(f"- Trend: {recent_price_action['trend']}")
        
        return "\n".join(lines)
    
    def create_prompt(self, technical_data: str) -> str:
        """
        Create comprehensive prompt for OpenAI
        
        Args:
            technical_data: Formatted technical analysis data
        
        Returns:
            Complete prompt string
        """
        prompt = f"""You are an experienced technical analyst specializing in Vietnamese stock market analysis. 
Analyze the following technical data and provide actionable trading suggestions.

{technical_data}

Please provide your analysis in the following structured format:

1. **Overall Recommendation**: (BUY / SELL / HOLD / REDUCE / DCA / INVEST MORE / ...)
2. **Risk Level**: 0-100
3. **Reasoning**: Provide a concise explanation based on the technical indicators and support/resistance zones
4. **Entry Strategy**: 
   - Suggested entry price or range
   - Conditions for entry
5. **Exit Strategy**:
   - Take profit target(s)
   - Stop-loss level
6. **Confidence Level**: 0-100 with a brief explanation
7. **Key Risks**: List 2-3 main risks to consider
8. **Time Horizon**: Suggested holding period (day trade / swing trade / position trade)

Important considerations:
- This is for Vietnamese stock market (VND currency)
- Consider both bullish and bearish scenarios
- Support/resistance zones with higher strength and more touches are more significant
- RSI above 70 suggests overbought conditions, below 30 suggests oversold
- MACD crossover signals can indicate trend changes
- Volume confirmation is important for breakouts
- Rules I often follow:
    + 30-30-40 rule when buying: First step buy buy 30% of the intended purchase amount, second step buy 30% of the intended purchase amount, third step buy 40% of the intended purchase amount.
    + When it break resistance zone with strong confidence, it's a good entry to buy more.
    + After it break resistance zone, if it break support zone with strong confidence, it's a good entry to sell more.

Provide clear, actionable recommendations suitable for retail traders.
"""
        return prompt
    
    async def get_trading_suggestions(self,
                                     ticker: str,
                                     current_price: float,
                                     indicators: Dict,
                                     zones: Optional[Dict] = None,
                                     signals: Optional[List[str]] = None,
                                     recent_price_action: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get trading suggestions from OpenAI based on technical analysis
        
        Args:
            ticker: Stock symbol
            current_price: Current stock price
            indicators: Dictionary with latest indicator values
            zones: Optional dictionary with support/resistance zones
            signals: Optional list of trading signals
            recent_price_action: Optional recent price action summary
        
        Returns:
            Dictionary with AI suggestions and analysis
        """
        try:
            # Format technical data
            technical_data = self.format_technical_data(
                ticker, current_price, indicators, zones or {}, signals or [], recent_price_action
            )
            
            # Create prompt
            prompt = self.create_prompt(technical_data)
            
            # Call OpenAI API (wrap in asyncio.to_thread to make it non-blocking)
            def _call_openai():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional technical analyst for Vietnamese stock market."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
            
            response = await asyncio.to_thread(_call_openai)
            
            # Extract response
            ai_content = response.choices[0].message.content
            
            # Try to parse structured response, fallback to raw text
            suggestions = {
                'ticker': ticker,
                'current_price': current_price,
                'raw_response': ai_content,
                'model_used': self.model,
                'parsed': self._parse_response(ai_content)
            }
            
            return suggestions
            
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e),
                'raw_response': None
            }
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse AI response to extract structured information
        
        Args:
            response_text: Raw AI response text
        
        Returns:
            Dictionary with parsed structured data
        """
        parsed = {
            'recommendation': None,
            'risk_level': None,
            'reasoning': None,
            'entry_strategy': None,
            'exit_strategy': None,
            'confidence_level': None,
            'key_risks': [],
            'time_horizon': None
        }
        
        try:
            lines = response_text.split('\n')
            current_section = None
            section_content = []
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Detect sections
                if 'recommendation' in line_lower and 'overall' in line_lower:
                    current_section = 'recommendation'
                    section_content = []
                    # Try to extract recommendation from same line
                    if 'BUY' in line.upper():
                        parsed['recommendation'] = 'BUY'
                    elif 'SELL' in line.upper():
                        parsed['recommendation'] = 'SELL'
                    elif 'HOLD' in line.upper():
                        parsed['recommendation'] = 'HOLD'
                elif 'risk level' in line_lower:
                    current_section = 'risk_level'
                    section_content = []
                    if 'LOW' in line.upper():
                        parsed['risk_level'] = 'LOW'
                    elif 'MODERATE' in line.upper():
                        parsed['risk_level'] = 'MODERATE'
                    elif 'HIGH' in line.upper():
                        parsed['risk_level'] = 'HIGH'
                elif 'reasoning' in line_lower:
                    current_section = 'reasoning'
                    section_content = []
                elif 'entry strategy' in line_lower:
                    current_section = 'entry_strategy'
                    section_content = []
                elif 'exit strategy' in line_lower:
                    current_section = 'exit_strategy'
                    section_content = []
                elif 'confidence level' in line_lower:
                    current_section = 'confidence_level'
                    section_content = []
                elif 'key risks' in line_lower:
                    current_section = 'key_risks'
                    section_content = []
                elif 'time horizon' in line_lower:
                    current_section = 'time_horizon'
                    section_content = []
                elif line.strip().startswith('-') or line.strip().startswith('•'):
                    # List item
                    if current_section == 'key_risks':
                        parsed['key_risks'].append(line.strip().lstrip('-').lstrip('•').strip())
                    elif current_section and section_content is not None:
                        section_content.append(line)
                elif line.strip() and not line.strip().startswith('#'):
                    # Regular content line
                    if current_section:
                        section_content.append(line.strip())
                
                # Store accumulated content
                if current_section and section_content:
                    content_text = ' '.join(section_content).strip()
                    if current_section == 'reasoning' and not parsed['reasoning']:
                        parsed['reasoning'] = content_text
                    elif current_section == 'entry_strategy' and not parsed['entry_strategy']:
                        parsed['entry_strategy'] = content_text
                    elif current_section == 'exit_strategy' and not parsed['exit_strategy']:
                        parsed['exit_strategy'] = content_text
                    elif current_section == 'time_horizon' and not parsed['time_horizon']:
                        parsed['time_horizon'] = content_text
                    elif current_section == 'confidence_level' and not parsed['confidence_level']:
                        # Try to extract confidence from content
                        if 'VERY HIGH' in content_text.upper():
                            parsed['confidence_level'] = 'VERY HIGH'
                        elif 'HIGH' in content_text.upper():
                            parsed['confidence_level'] = 'HIGH'
                        elif 'MODERATE' in content_text.upper():
                            parsed['confidence_level'] = 'MODERATE'
                        elif 'LOW' in content_text.upper():
                            parsed['confidence_level'] = 'LOW'
                        
        except Exception as e:
            # If parsing fails, just return what we have
            pass
        
        return parsed
    
    def format_suggestions_output(self, suggestions: Dict[str, Any]) -> str:
        """
        Format AI suggestions for console output
        
        Args:
            suggestions: Dictionary with AI suggestions
        
        Returns:
            Formatted string for display
        """
        if 'error' in suggestions:
            return f"❌ Error getting AI suggestions: {suggestions['error']}"
        
        lines = [
            "\n🤖 AI Trading Suggestions",
            "=" * 70,
        ]
        
        parsed = suggestions.get('parsed', {})
        
        # Overall Recommendation
        recommendation = parsed.get('recommendation') or 'N/A'
        rec_emoji = "🟢" if recommendation == "BUY" else "🔴" if recommendation == "SELL" else "🟡"
        lines.append(f"\n{rec_emoji} **Overall Recommendation:** {recommendation}")
        
        # Risk Level
        risk_level = parsed.get('risk_level') or 'N/A'
        lines.append(f"⚠️  **Risk Level:** {risk_level}")
        
        # Confidence Level
        confidence = parsed.get('confidence_level') or 'N/A'
        lines.append(f"🎯 **Confidence Level:** {confidence}")
        
        # Reasoning
        if parsed.get('reasoning'):
            lines.append(f"\n💭 **Reasoning:**")
            lines.append(f"   {parsed['reasoning']}")
        
        # Entry Strategy
        if parsed.get('entry_strategy'):
            lines.append(f"\n📥 **Entry Strategy:**")
            lines.append(f"   {parsed['entry_strategy']}")
        
        # Exit Strategy
        if parsed.get('exit_strategy'):
            lines.append(f"\n📤 **Exit Strategy:**")
            lines.append(f"   {parsed['exit_strategy']}")
        
        # Key Risks
        if parsed.get('key_risks'):
            lines.append(f"\n⚠️  **Key Risks:**")
            for risk in parsed['key_risks']:
                lines.append(f"   • {risk}")
        
        # Time Horizon
        if parsed.get('time_horizon'):
            lines.append(f"\n⏰ **Time Horizon:** {parsed['time_horizon']}")
        
        # Full response
        if suggestions.get('raw_response'):
            lines.append(f"\n📄 **Full AI Analysis:**")
            lines.append("   " + "\n   ".join(suggestions['raw_response'].split('\n')))
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def format_portfolio_data(self, 
                             portfolio_data: Dict[str, Any],
                             ta_results: Dict[str, Any],
                             portfolio_summary: Dict[str, Any]) -> str:
        """
        Format portfolio data and TA results for OpenAI portfolio analysis
        
        Args:
            portfolio_data: Portfolio dictionary with stocks and cash
            ta_results: Dictionary with TA results for each stock
            portfolio_summary: Portfolio summary metrics
            
        Returns:
            Formatted string with portfolio data
        """
        lines = [
            "## Portfolio Analysis Request",
            f"\n**Analysis Date:** {portfolio_summary.get('analysis_timestamp', 'N/A')}",
        ]
        
        # Portfolio Summary
        cash_balance = portfolio_data.get("cash_balance", {})
        lines.append("\n### Portfolio Summary:")
        lines.append(f"- Total Positions: {portfolio_summary.get('total_positions', 0)}")
        lines.append(f"- Total Portfolio Value: {portfolio_summary.get('total_value', 0):,.0f} VND")
        lines.append(f"- Total Cost Basis: {portfolio_summary.get('total_cost', 0):,.0f} VND")
        lines.append(f"- Total P&L: {portfolio_summary.get('total_pnl', 0):,.0f} VND ({portfolio_summary.get('total_pnl_pct', 0):+.2f}%)")
        lines.append(f"- Cash Balance: {cash_balance.get('balance', 0):,.0f} {cash_balance.get('currency', 'VND')}")
        
        # Individual Stock Analysis
        lines.append("\n### Individual Stock Analysis:")
        
        for symbol, ta_result in ta_results.items():
            if "error" in ta_result:
                lines.append(f"\n#### {symbol}")
                lines.append(f"⚠️  Error: {ta_result['error']}")
                continue
            
            stock = ta_result.get("stock", {})
            current_price = ta_result.get("current_price", 0)
            indicators = ta_result.get("indicators", {})
            zones = ta_result.get("support_resistance", {})
            
            lines.append(f"\n#### {symbol}")
            lines.append(f"**Position:**")
            lines.append(f"- Shares: {stock.get('total_shares', 0):,}")
            lines.append(f"- Avg Buy Price: {stock.get('avg_buy_price', 0):,.2f} VND")
            # current_price is in full VND format
            lines.append(f"- Current Price: {current_price:,.2f} VND")
            lines.append(f"- Position Value: {ta_result.get('position_value', 0):,.0f} VND")
            lines.append(f"- P&L: {ta_result.get('position_pnl', 0):,.0f} VND ({ta_result.get('position_pnl_pct', 0):+.2f}%)")
            lines.append(f"- Buy Method: {stock.get('buy_method', 'N/A')}")
            if stock.get('sector'):
                lines.append(f"- Sector: {stock.get('sector')}")
            if stock.get('note'):
                lines.append(f"- Note: {stock.get('note')}")
            
            # Transaction History
            transactions = ta_result.get("transaction_history", [])
            if transactions:
                lines.append(f"\n**Transaction History:** ({len(transactions)} transactions)")
                for txn in transactions[-5:]:  # Show last 5 transactions
                    txn_type = txn.get("type", "unknown")
                    txn_date = txn.get("date", "N/A")
                    txn_shares = txn.get("shares", 0)
                    txn_price = txn.get("price", 0)
                    if txn_type == "buy":
                        lines.append(f"  - {txn_date}: BUY {txn_shares} @ {txn_price:,.2f} VND (Cost: {txn.get('total_cost', 0):,.0f} VND)")
                    else:
                        lines.append(f"  - {txn_date}: SELL {txn_shares} @ {txn_price:,.2f} VND (Proceeds: {txn.get('total_proceeds', 0):,.0f} VND)")
            
            # Technical Indicators
            lines.append(f"\n**Technical Indicators:**")
            if pd.notna(indicators.get('sma_20')):
                lines.append(f"- SMA(20): {indicators['sma_20']:,.2f}")
            if pd.notna(indicators.get('sma_50')):
                lines.append(f"- SMA(50): {indicators['sma_50']:,.2f}")
            if pd.notna(indicators.get('rsi_14')):
                lines.append(f"- RSI(14): {indicators['rsi_14']:.2f}")
            if pd.notna(indicators.get('macd')):
                lines.append(f"- MACD: {indicators['macd']:.2f}")
            if pd.notna(indicators.get('macd_signal')):
                lines.append(f"- MACD Signal: {indicators['macd_signal']:.2f}")
            if pd.notna(indicators.get('volume_ratio')):
                lines.append(f"- Volume Ratio: {indicators['volume_ratio']:.2f}")
            
            # Support/Resistance
            # Zones are now in full VND format (converted in analyzer)
            if zones:
                if zones.get('resistance_zones'):
                    lines.append(f"\n**Nearest Resistance:**")
                    nearest_res = zones['resistance_zones'][0] if zones['resistance_zones'] else None
                    if nearest_res:
                        resistance_middle = nearest_res.get('middle', 0)
                        resistance_distance = nearest_res.get('distance_pct', 0)
                        direction = "above" if resistance_distance > 0 else "below"
                        lines.append(f"- Zone: {resistance_middle:,.2f} VND")
                        lines.append(f"- Distance: {abs(resistance_distance):.2f}% {direction}")
                        lines.append(f"- Strength: {nearest_res.get('strength', 0):.2f}")
                
                if zones.get('support_zones'):
                    lines.append(f"\n**Nearest Support:**")
                    nearest_sup = zones['support_zones'][0] if zones['support_zones'] else None
                    if nearest_sup:
                        support_middle = nearest_sup.get('middle', 0)
                        support_distance = nearest_sup.get('distance_pct', 0)
                        direction = "below" if support_distance < 0 else "above"
                        lines.append(f"- Zone: {support_middle:,.2f} VND")
                        lines.append(f"- Distance: {abs(support_distance):.2f}% {direction}")
                        lines.append(f"- Strength: {nearest_sup.get('strength', 0):.2f}")
        
        return "\n".join(lines)
    
    def create_portfolio_prompt(self, portfolio_data: str) -> str:
        """
        Create comprehensive prompt for portfolio-level analysis
        
        Args:
            portfolio_data: Formatted portfolio and TA data
            
        Returns:
            Complete prompt string for portfolio analysis
        """
        prompt = f"""You are an experienced portfolio manager and technical analyst specializing in Vietnamese stock market.
Analyze the following portfolio data and provide comprehensive investment advice.

{portfolio_data}

Please provide your analysis in the following structured format:

## Portfolio-Level Recommendations

1. **Overall Portfolio Assessment**: 
   - Overall market outlook
   - Portfolio health and performance
   - Risk assessment

2. **Portfolio Strategy**:
   - Rebalancing suggestions (if needed)
   - Diversification assessment
   - Cash management recommendations

3. **Individual Stock Recommendations** (for each stock):
   - **Action**: BUY MORE / SELL / HOLD / REDUCE
   - **Reasoning**: Brief explanation based on TA and position
   - **Target Price**: Suggested entry/exit price
   - **Stop Loss**: If applicable
   - **Confidence**: LOW / MODERATE / HIGH

4. **Risk Management**:
   - Portfolio-level risks
   - Position sizing recommendations
   - Sector concentration concerns

5. **Action Items**:
   - Priority actions to take
   - Watchlist items
   - Key levels to monitor

Important considerations:
- This is for Vietnamese stock market (VND currency)
- Consider transaction history and cost basis
- Factor in current market conditions and technical indicators
- Provide actionable, practical advice
- Consider both bullish and bearish scenarios
- Account for cash balance and liquidity needs
- Transaction history shows purchase patterns (DCA, lump sum, etc.)

Provide clear, actionable portfolio management recommendations suitable for retail investors.
"""
        return prompt
    
    async def get_portfolio_advice(self,
                                  portfolio_data: Dict[str, Any],
                                  ta_results: Dict[str, Any],
                                  portfolio_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get portfolio-level investment advice from OpenAI
        
        Args:
            portfolio_data: Portfolio dictionary with stocks and cash
            ta_results: Dictionary with TA results for each stock
            portfolio_summary: Portfolio summary metrics
            
        Returns:
            Dictionary with AI portfolio advice
        """
        try:
            # Format portfolio data
            formatted_data = self.format_portfolio_data(
                portfolio_data, ta_results, portfolio_summary
            )
            
            # Create prompt
            prompt = self.create_portfolio_prompt(formatted_data)
            
            # Call OpenAI API
            def _call_openai():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional portfolio manager and technical analyst for Vietnamese stock market."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=3000
                )
            
            response = await asyncio.to_thread(_call_openai)
            
            # Extract response
            ai_content = response.choices[0].message.content
            
            return {
                'portfolio_summary': portfolio_summary,
                'raw_response': ai_content,
                'model_used': self.model,
                'analysis_timestamp': portfolio_summary.get('analysis_timestamp')
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'raw_response': None,
                'portfolio_summary': portfolio_summary
            }

