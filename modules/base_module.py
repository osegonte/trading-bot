"""
Base interface for all trading modules
Provides standardized structure for analysis modules
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
import pandas as pd


class TradingModule(ABC):
    """
    Abstract base class for all trading modules
    
    All modules must implement get_signal() method
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize module
        
        Args:
            name: Module identifier (e.g., 'rsi', 'macd')
            config: Configuration dictionary with parameters
        """
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.weight = config.get('weight', 1.0)
        
        # Validate configuration
        self.validate_config()
    
    @abstractmethod
    def get_signal(self, df: pd.DataFrame, **kwargs) -> Tuple[str, str, int]:
        """
        Analyze market data and return trading signal
        
        Args:
            df: DataFrame with OHLC data (columns: Open, High, Low, Close, Volume)
            **kwargs: Additional parameters (e.g., current_price, macro_data)
        
        Returns:
            Tuple of (verdict, explanation, confidence)
            - verdict: 'BUY', 'SELL', or 'NEUTRAL'
            - explanation: Human-readable reasoning (str)
            - confidence: Confidence level 0-100 (int)
        
        Example:
            >>> module.get_signal(df)
            ('BUY', 'RSI 25 oversold', 75)
        """
        pass
    
    def validate_config(self) -> None:
        """
        Validate module configuration
        Override in subclass for custom validation
        """
        required_keys = ['enabled', 'weight']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        
        # Validate weight
        if not 0 <= self.config['weight'] <= 2.0:
            raise ValueError(f"Weight must be between 0 and 2.0, got {self.config['weight']}")
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update module configuration at runtime
        
        Args:
            new_config: Dictionary with new configuration values
        """
        self.config.update(new_config)
        self.weight = self.config.get('weight', self.weight)
        self.enabled = self.config.get('enabled', self.enabled)
        self.validate_config()
    
    def __repr__(self) -> str:
        """String representation of module"""
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__}(name={self.name}, weight={self.weight}, {status})>"
