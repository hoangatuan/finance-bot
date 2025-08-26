"""
Factory pattern for creating data fetchers
"""
from typing import Dict, Type
from .base_fetcher import BaseFetcher
from .vnstock_fetcher import VNStockFetcher


class FetcherFactory:
    """Factory for creating data fetchers"""
    
    _fetchers: Dict[str, Type[BaseFetcher]] = {
        'vnstock': VNStockFetcher,
    }
    
    @classmethod
    def create_fetcher(cls, source: str, **kwargs) -> BaseFetcher:
        """
        Create a fetcher instance
        
        Args:
            source: Data source name ('vnstock', etc.)
            **kwargs: Additional arguments for fetcher constructor
            
        Returns:
            Fetcher instance
            
        Raises:
            ValueError: If source is not supported
        """
        if source not in cls._fetchers:
            supported = ', '.join(cls._fetchers.keys())
            raise ValueError(f"Unsupported data source: {source}. Supported: {supported}")
        
        fetcher_class = cls._fetchers[source]
        return fetcher_class(**kwargs)
    
    @classmethod
    def register_fetcher(cls, name: str, fetcher_class: Type[BaseFetcher]):
        """
        Register a new fetcher type
        
        Args:
            name: Name for the fetcher
            fetcher_class: Fetcher class to register
        """
        cls._fetchers[name] = fetcher_class
    
    @classmethod
    def get_supported_sources(cls) -> list:
        """Get list of supported data sources"""
        return list(cls._fetchers.keys())
    
    @classmethod
    def get_fetcher_class(cls, source: str) -> Type[BaseFetcher]:
        """
        Get fetcher class without creating instance
        
        Args:
            source: Data source name
            
        Returns:
            Fetcher class
        """
        if source not in cls._fetchers:
            raise ValueError(f"Unsupported data source: {source}")
        
        return cls._fetchers[source]
