"""
Portfolio Manager - JSON-based portfolio storage with price conversion
"""
import json
import os
import fcntl
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class PortfolioManager:
    """Manages portfolio data stored in JSON format with price conversion"""
    
    # Price conversion factor: divide by 1000 for storage
    PRICE_DIVISOR = 1000.0
    
    def __init__(self, portfolio_path: Optional[str] = None):
        """
        Initialize Portfolio Manager
        
        Args:
            portfolio_path: Path to portfolio JSON file. If None, uses data/portfolio.json
        """
        if portfolio_path is None:
            # Default path: data/portfolio.json relative to project root
            project_root = Path(__file__).parent.parent.parent
            portfolio_path = project_root / "data" / "portfolio.json"
        
        self.portfolio_path = Path(portfolio_path)
        self.portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _price_to_storage(price: float) -> float:
        """
        Convert price to storage format (divide by 1000)
        
        Args:
            price: Price in full format (e.g., 24500.0 VND)
            
        Returns:
            Price in storage format (e.g., 24.5)
        """
        return price / PortfolioManager.PRICE_DIVISOR
    
    @staticmethod
    def _price_from_storage(price: float) -> float:
        """
        Convert price from storage format (multiply by 1000)
        
        Args:
            price: Price in storage format (e.g., 24.5)
            
        Returns:
            Price in full format (e.g., 24500.0 VND)
        """
        return price * PortfolioManager.PRICE_DIVISOR
    
    def _load_json_file(self) -> Dict[str, Any]:
        """
        Load JSON file with file locking
        
        Returns:
            Portfolio data dictionary
        """
        if not self.portfolio_path.exists():
            # Return default empty portfolio
            return {
                "cash_balance": {
                    "balance": 0.0,
                    "currency": "VND",
                    "updated_at": datetime.now().isoformat()
                },
                "stocks": [],
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_stocks": 0
                }
            }
        
        with open(self.portfolio_path, 'r', encoding='utf-8') as f:
            # Use file locking (Unix/Linux/Mac)
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (OSError, AttributeError):
                # Windows or file locking not available, just read
                data = json.load(f)
        
        return data
    
    def _save_json_file(self, data: Dict[str, Any]) -> None:
        """
        Save JSON file with atomic write and file locking
        
        Args:
            data: Portfolio data dictionary to save
        """
        # Update metadata
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        data["metadata"]["total_stocks"] = len(data.get("stocks", []))
        
        # Create temp file for atomic write
        temp_path = self.portfolio_path.with_suffix('.json.tmp')
        
        # Write to temp file
        with open(temp_path, 'w', encoding='utf-8') as f:
            try:
                # Try to acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except (OSError, AttributeError):
                # Windows or file locking not available, continue without lock
                pass
            
            json.dump(data, f, indent=2, ensure_ascii=False)
            
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (OSError, AttributeError):
                pass
        
        # Atomic move (rename) - works on Unix and Windows
        temp_path.replace(self.portfolio_path)
    
    def load_portfolio(self) -> Dict[str, Any]:
        """
        Load portfolio from JSON and convert prices from storage format
        
        Returns:
            Portfolio dictionary with prices in full format (multiplied by 1000)
        """
        data = self._load_json_file()
        
        # Convert cash balance
        if "cash_balance" in data and "balance" in data["cash_balance"]:
            data["cash_balance"]["balance"] = self._price_from_storage(
                data["cash_balance"]["balance"]
            )
        
        # Convert stock prices
        for stock in data.get("stocks", []):
            if "avg_buy_price" in stock:
                stock["avg_buy_price"] = self._price_from_storage(stock["avg_buy_price"])
            
            # Convert transaction prices
            for txn in stock.get("transactions", []):
                if "price" in txn:
                    txn["price"] = self._price_from_storage(txn["price"])
                if "total_cost" in txn:
                    txn["total_cost"] = self._price_from_storage(txn["total_cost"])
                if "total_proceeds" in txn:
                    txn["total_proceeds"] = self._price_from_storage(txn["total_proceeds"])
        
        return data
    
    def save_portfolio(self, portfolio_data: Dict[str, Any]) -> None:
        """
        Save portfolio to JSON and convert prices to storage format
        
        Args:
            portfolio_data: Portfolio dictionary with prices in full format
        """
        # Deep copy to avoid modifying original
        data = json.loads(json.dumps(portfolio_data))
        
        # Convert cash balance
        if "cash_balance" in data and "balance" in data["cash_balance"]:
            data["cash_balance"]["balance"] = self._price_to_storage(
                data["cash_balance"]["balance"]
            )
        
        # Convert stock prices
        for stock in data.get("stocks", []):
            if "avg_buy_price" in stock:
                stock["avg_buy_price"] = self._price_to_storage(stock["avg_buy_price"])
            
            # Convert transaction prices
            for txn in stock.get("transactions", []):
                if "price" in txn:
                    txn["price"] = self._price_to_storage(txn["price"])
                if "total_cost" in txn:
                    txn["total_cost"] = self._price_to_storage(txn["total_cost"])
                if "total_proceeds" in txn:
                    txn["total_proceeds"] = self._price_to_storage(txn["total_proceeds"])
        
        self._save_json_file(data)
    
    def get_portfolio(self) -> Dict[str, Any]:
        """
        Get portfolio with prices in full format (alias for load_portfolio)
        
        Returns:
            Portfolio dictionary with prices in full format
        """
        return self.load_portfolio()
    
    def get_portfolio_file_path(self) -> str:
        """
        Get the path to the portfolio JSON file
        
        Returns:
            Absolute path to portfolio.json
        """
        return str(self.portfolio_path.absolute())

