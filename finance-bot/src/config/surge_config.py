"""
Surge Detection Configuration
Loads and manages configuration for surge monitoring
"""
import os
import yaml
from typing import List, Dict, Optional
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

try:
    from ..notify.lark import LarkNotifier
except ImportError:
    from notify.lark import LarkNotifier


class SurgeConfig:
    """
    Manages configuration for surge monitoring
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to monitored_tickers.yaml file
                        If None, uses default path: finance-bot/config/monitored_tickers.yaml
        """
        if config_path is None:
            # Default path: finance-bot/config/monitored_tickers.yaml
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / 'config' / 'monitored_tickers.yaml'
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """
        Load configuration from YAML file
        
        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            # Return default config if file doesn't exist
            return {
                'tickers': [],
                'surge_thresholds': {
                    'volume_multiplier': 1.5,
                    'price_change_pct': 3.0
                }
            }
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Error loading config from {self.config_path}: {e}")
            return {
                'tickers': [],
                'surge_thresholds': {
                    'volume_multiplier': 1.5,
                    'price_change_pct': 3.0
                }
            }
    
    def get_tickers(self) -> List[str]:
        """
        Get list of tickers to monitor
        
        Returns:
            List of ticker symbols
        """
        tickers = self.config.get('tickers', [])
        
        # Also check environment variable (comma-separated)
        env_tickers = os.getenv('MONITORED_TICKERS')
        if env_tickers:
            env_ticker_list = [t.strip().upper() for t in env_tickers.split(',')]
            # Merge with config, removing duplicates
            tickers = list(set(tickers + env_ticker_list))
        
        return tickers
    
    def get_volume_multiplier(self) -> float:
        """
        Get volume surge threshold multiplier
        
        Returns:
            Volume multiplier (default: 1.5)
        """
        threshold = self.config.get('surge_thresholds', {}).get('volume_multiplier')
        if threshold is not None:
            return float(threshold)
        
        # Check environment variable
        env_value = os.getenv('SURGE_VOLUME_MULTIPLIER')
        if env_value:
            return float(env_value)
        
        return 1.5
    
    def get_price_change_pct(self) -> float:
        """
        Get price surge threshold percentage
        
        Returns:
            Price change percentage (default: 3.0)
        """
        threshold = self.config.get('surge_thresholds', {}).get('price_change_pct')
        if threshold is not None:
            return float(threshold)
        
        # Check environment variable
        env_value = os.getenv('SURGE_PRICE_CHANGE_PCT')
        if env_value:
            return float(env_value)
        
        return 3.0
    
    def get_lark_notifier(self) -> Optional[LarkNotifier]:
        """
        Create and return LarkNotifier instance from environment variables
        
        Returns:
            LarkNotifier instance or None if webhook URL not available
        """
        try:
            return LarkNotifier()
        except ValueError:
            # Webhook URL not set
            return None
    
    def reload(self):
        """
        Reload configuration from file
        """
        self.config = self._load_config()

