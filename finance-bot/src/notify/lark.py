"""
Lark Notification Module
Sends notifications to Lark group chats using webhook URLs
"""
import os
import json
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

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


class LarkNotifier:
    """
    Sends messages to Lark group chats using webhook URLs
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Lark notifier with webhook URL
        
        Args:
            webhook_url: Lark webhook URL (from environment if not provided)
        """
        self.webhook_url = webhook_url or os.getenv('LARK_WEBHOOK_URL')
        
        if not self.webhook_url:
            raise ValueError("LARK_WEBHOOK_URL must be set")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_message(
        self,
        text: str,
        msg_type: str = "text"
    ) -> Dict:
        """
        Send a text message to Lark group via webhook
        
        Args:
            text: Message text content
            msg_type: Message type (default: "text")
        
        Returns:
            Response dictionary
        """
        # Prepare message payload
        # Lark webhook expects JSON with msg_type and content
        payload = {
            "msg_type": msg_type,
            "content": {
                "text": text
            }
        }
        
        # Create SSL context that doesn't verify certificates (for testing)
        # In production, you should fix SSL certificates instead
        ssl_context = None
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass  # Use default SSL context if creation fails
        
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False  # Disable SSL verification for now
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            response_data = json.loads(response_text)
                            # Lark webhook returns {"code": 0, "msg": "success"} on success
                            if response_data.get("code") == 0:
                                return {
                                    "success": True,
                                    "response": response_data
                                }
                            else:
                                error_msg = response_data.get("msg", "Unknown error")
                                error_code = response_data.get("code", "unknown")
                                raise Exception(f"Lark webhook error (code {error_code}): {error_msg}")
                        except json.JSONDecodeError:
                            # Some webhooks return plain text
                            if "success" in response_text.lower() or response.status == 200:
                                return {
                                    "success": True,
                                    "response": response_text
                                }
                            else:
                                raise Exception(f"Unexpected response: {response_text}")
                    else:
                        raise Exception(f"HTTP {response.status}: {response_text}")
                        
            except aiohttp.ClientError as e:
                raise Exception(f"Network error sending to Lark webhook: {str(e)}")
            except asyncio.TimeoutError:
                raise Exception(f"Timeout sending to Lark webhook (10s)")
            except Exception as e:
                # Re-raise with more context
                raise Exception(f"Failed to send Lark webhook message: {str(e)}")
    
    async def send_card(
        self,
        card_content: Dict
    ) -> Dict:
        """
        Send a rich card message to Lark via webhook
        
        Args:
            card_content: Card content dictionary following Lark card format
        
        Returns:
            Response dictionary
        """
        payload = {
            "msg_type": "interactive",
            "card": card_content
        }
        
        # Create SSL context that doesn't verify certificates (for testing)
        ssl_context = None
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass
        
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False  # Disable SSL verification for now
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            response_data = json.loads(response_text)
                            if response_data.get("code") == 0:
                                return {
                                    "success": True,
                                    "response": response_data
                                }
                            else:
                                error_msg = response_data.get("msg", "Unknown error")
                                raise Exception(f"Lark webhook error: {error_msg}")
                        except json.JSONDecodeError:
                            if response.status == 200:
                                return {
                                    "success": True,
                                    "response": response_text
                                }
                            else:
                                raise Exception(f"Unexpected response: {response_text}")
                    else:
                        raise Exception(f"HTTP {response.status}: {response_text}")
                        
            except aiohttp.ClientError as e:
                raise Exception(f"Failed to send Lark webhook card: {e}")
    
    async def send_analysis(
        self,
        ticker: str,
        surge_data: Dict,
        analysis_data: Optional[Dict] = None,
        processed_df: Optional[Any] = None
    ) -> Dict:
        """
        Format and send surge analysis report to Lark
        
        Args:
            ticker: Stock ticker symbol
            surge_data: Surge detection results from SurgeDetector
            analysis_data: Optional comprehensive analysis data from analyze_ticker_multi_timeframe
        
        Returns:
            Response dictionary from send_message
        """
        # Build message text
        lines = []
        
        # Header
        lines.append(f"📈 **Surge Alert: {ticker}**")
        lines.append("=" * 40)
        
        # Surge detection details
        volume_surge = surge_data.get('volume_surge', {})
        price_surge = surge_data.get('price_surge', {})
        
        # Always show volume information (even if not a surge)
        current_vol = volume_surge.get('current_volume', 0)
        avg_vol = volume_surge.get('average_volume', 0)
        vol_ratio = volume_surge.get('volume_ratio', 0)
        
        # Get volume ratios from indicators if available
        vol_ratio_20 = None
        vol_ratio_50 = None
        
        # First try to get from processed_df if available
        if processed_df is not None:
            try:
                import pandas as pd
                import numpy as np
                if not processed_df.empty and 'vol_ratio_20' in processed_df.columns:
                    vol_val = processed_df['vol_ratio_20'].iloc[-1]
                    # Check if value is valid (not NaN, not None, not inf)
                    if pd.notna(vol_val) and np.isfinite(vol_val):
                        vol_ratio_20 = float(vol_val)
                if not processed_df.empty and 'vol_ratio_50' in processed_df.columns:
                    vol_val = processed_df['vol_ratio_50'].iloc[-1]
                    # Check if value is valid (not NaN, not None, not inf)
                    if pd.notna(vol_val) and np.isfinite(vol_val):
                        vol_ratio_50 = float(vol_val)
            except Exception:
                pass
        
        # Fallback: Try to get from analysis_data
        if (vol_ratio_20 is None or vol_ratio_50 is None) and analysis_data:
            timeframes = analysis_data.get('timeframes', {})
            for tf, tf_data in timeframes.items():
                if 'error' not in tf_data:
                    latest_data = tf_data.get('latest_data', {})
                    if latest_data:
                        if vol_ratio_20 is None:
                            vol_ratio_20 = latest_data.get('vol_ratio_20')
                        if vol_ratio_50 is None:
                            vol_ratio_50 = latest_data.get('vol_ratio_50')
                        if vol_ratio_20 and vol_ratio_50:
                            break
        
        lines.append(f"\n📊 **Volume Information**")
        if current_vol > 0:
            lines.append(f"   Current Volume: {current_vol:,.0f}")
        if avg_vol > 0:
            lines.append(f"   Average Volume: {avg_vol:,.0f}")
        if vol_ratio > 0:
            lines.append(f"   Volume Ratio: {vol_ratio:.2f}x")
        
        # Only show volume ratios if they have valid values
        import pandas as pd
        import numpy as np
        if vol_ratio_20 is not None:
            try:
                if pd.notna(vol_ratio_20) and np.isfinite(vol_ratio_20):
                    lines.append(f"   Volume Ratio (20): {vol_ratio_20:.2f}x")
                else:
                    lines.append(f"   Volume Ratio (20): N/A (insufficient data)")
            except Exception:
                lines.append(f"   Volume Ratio (20): N/A")
        
        if vol_ratio_50 is not None:
            try:
                if pd.notna(vol_ratio_50) and np.isfinite(vol_ratio_50):
                    lines.append(f"   Volume Ratio (50): {vol_ratio_50:.2f}x")
                else:
                    lines.append(f"   Volume Ratio (50): N/A (need 50+ days of data)")
            except Exception:
                lines.append(f"   Volume Ratio (50): N/A")
        elif processed_df is not None:
            # Check if we have enough data for 50-period calculation
            try:
                if len(processed_df) < 50:
                    lines.append(f"   Volume Ratio (50): N/A (only {len(processed_df)} days available, need 50+)")
            except Exception:
                pass
        
        if volume_surge.get('is_surge'):
            lines.append(f"   ⚠️ **VOLUME SURGE DETECTED**")
        
        # Price information
        current_price = price_surge.get('current_price', 0)
        if current_price > 0:
            lines.append(f"\n💰 **Price Information**")
            lines.append(f"   Current Price: {current_price:,.2f} VND")
        
        if price_surge.get('is_surge'):
            price_change_pct = price_surge.get('price_change_pct', 0)
            direction = price_surge.get('direction', 'up')
            direction_emoji = "📈" if direction == 'up' else "📉"
            lines.append(f"   {direction_emoji} **PRICE SURGE DETECTED**")
            lines.append(f"   Price Change: {price_change_pct:+.2f}%")
        
        # Analysis data (if available)
        if analysis_data:
            timeframes = analysis_data.get('timeframes', {})
            ai_analysis = analysis_data.get('ai_analysis', {})
            
            # Add timeframe indicators
            if timeframes:
                lines.append(f"\n📊 **Technical Indicators**")
                for tf, tf_data in timeframes.items():
                    if 'error' not in tf_data:
                        indicators = tf_data.get('indicators', {})
                        if indicators:
                            rsi = indicators.get('rsi_14')
                            sma20 = indicators.get('sma_20')
                            if rsi:
                                lines.append(f"   {tf} RSI(14): {rsi:.2f}")
                            if sma20:
                                lines.append(f"   {tf} SMA(20): {sma20:,.2f}")
            
            # Add AI analysis if available
            if ai_analysis and 'error' not in ai_analysis:
                lines.append(f"\n🤖 **AI Analysis**")
                
                # Try multiple fields for AI response
                ai_text = None
                
                # Check for raw_response first (most complete)
                if ai_analysis.get('raw_response'):
                    ai_text = ai_analysis.get('raw_response')
                # Check for suggestion
                elif ai_analysis.get('suggestion'):
                    ai_text = ai_analysis.get('suggestion')
                # Check for reasoning
                elif ai_analysis.get('reasoning'):
                    ai_text = ai_analysis.get('reasoning')
                # Check for recommendation
                elif ai_analysis.get('recommendation'):
                    ai_text = ai_analysis.get('recommendation')
                
                if ai_text:
                    # Format the AI response - split into lines and add proper formatting
                    ai_lines = ai_text.split('\n')
                    for line in ai_lines:
                        line = line.strip()
                        if line:
                            # Keep headers as-is, indent body text
                            if line.startswith('#') or line.startswith('**'):
                                lines.append(f"   {line}")
                            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                                lines.append(f"   {line}")
                            else:
                                lines.append(f"   {line}")
                else:
                    # If no text found, show structured data
                    if ai_analysis.get('recommendation'):
                        lines.append(f"   Recommendation: {ai_analysis.get('recommendation')}")
                    if ai_analysis.get('risk_level'):
                        lines.append(f"   Risk Level: {ai_analysis.get('risk_level')}")
                    if ai_analysis.get('confidence_level'):
                        lines.append(f"   Confidence: {ai_analysis.get('confidence_level')}")
                    if not any([ai_analysis.get('recommendation'), ai_analysis.get('risk_level'), ai_analysis.get('confidence_level')]):
                        lines.append(f"   (AI analysis data available but no text content found)")
                        lines.append(f"   Available fields: {', '.join(ai_analysis.keys())}")
        
        # Timestamp
        timestamp = surge_data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        lines.append(f"\n⏰ {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Join all lines
        message_text = "\n".join(lines)
        
        # Send message
        return await self.send_message(message_text)
    
    def format_simple_alert(
        self,
        ticker: str,
        message: str
    ) -> str:
        """
        Format a simple alert message
        
        Args:
            ticker: Stock ticker symbol
            message: Alert message
        
        Returns:
            Formatted message string
        """
        return f"📈 **{ticker} Alert**\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
