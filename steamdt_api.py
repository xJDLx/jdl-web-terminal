import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TypedDict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class PriceData(TypedDict):
    sellPrice: float
    sellCount: int
    platform: str

class ItemResponse(BaseModel):
    success: bool
    data: Optional[List[PriceData]]
    errorMsg: Optional[str]

class SteamdtAPIException(Exception):
    """Custom exception for SteamDT API errors"""
    pass

class SteamdtAPI:
    """Steamdt.com API client for CS2 item monitoring"""
    
    BASE_URL = os.getenv("STEAMDT_BASE_URL", "https://open.steamdt.com")
    
    def __init__(self, api_key: str):
        """
        Initialize API client with API key
        
        Args:
            api_key: Bearer token from Steamdt account
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_item_price(self, market_hash_name: str) -> Optional[Dict]:
        """
        Get current price for a CS2 item
        
        Args:
            market_hash_name: Item market hash name (e.g., "AK-47 | Phantom Disruptor (Field-Tested)")
            
        Returns:
            Dictionary with price data or None if error
        """
        try:
            url = f"{self.BASE_URL}/open/cs2/v1/price"
            params = {"marketHashName": market_hash_name}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {})
            else:
                print(f"API Error: {data.get('errorMsg')}")
                return None
        except Exception as e:
            print(f"Error fetching price for {market_hash_name}: {e}")
            return None
    
    def get_batch_prices(self, market_hash_names: List[str]) -> Optional[Dict]:
        """
        Get prices for multiple items in one request
        
        Args:
            market_hash_names: List of market hash names
            
        Returns:
            Dictionary with batch price data or None if error
        """
        try:
            url = f"{self.BASE_URL}/open/cs2/v1/batch/price"
            payload = {"marketHashNames": market_hash_names}
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {})
            else:
                print(f"API Error: {data.get('errorMsg')}")
                return None
        except Exception as e:
            print(f"Error fetching batch prices: {e}")
            return None
    
    def get_average_price(self, market_hash_name: str) -> Optional[Dict]:
        """
        Get 7-day average price for an item
        
        Args:
            market_hash_name: Item market hash name
            
        Returns:
            Dictionary with average price data or None if error
        """
        try:
            url = f"{self.BASE_URL}/open/cs2/v1/avgPrice"
            params = {"marketHashName": market_hash_name}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {})
            else:
                print(f"API Error: {data.get('errorMsg')}")
                return None
        except Exception as e:
            print(f"Error fetching average price for {market_hash_name}: {e}")
            return None
    
    def get_item_info(self, pattern: str = "") -> Optional[Dict]:
        """
        Get CS2 item information
        
        Args:
            pattern: Optional search pattern for items
            
        Returns:
            Dictionary with item info or None if error
        """
        try:
            url = f"{self.BASE_URL}/open/cs2/v1/items"
            params = {}
            if pattern:
                params["pattern"] = pattern
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {})
            else:
                print(f"API Error: {data.get('errorMsg')}")
                return None
        except Exception as e:
            print(f"Error fetching item info: {e}")
            return None


def load_api_key(user_folder: str) -> Optional[str]:
    """
    Load API key from user's private config
    
    Args:
        user_folder: Path to user's private folder
        
    Returns:
        API key string or None if not found
    """
    try:
        config_file = os.path.join(user_folder, "steamdt_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("api_key")
    except Exception as e:
        print(f"Error loading API key: {e}")
    return None


def save_api_key(api_key: str, user_folder: str):
    """
    Save API key to user's private config
    
    Args:
        api_key: Steamdt API key
        user_folder: Path to user's private folder
    """
    try:
        if not os.path.exists(user_folder):
            os.makedirs(user_folder, exist_ok=True)
        
        config_file = os.path.join(user_folder, "steamdt_config.json")
        config = {"api_key": api_key, "timestamp": datetime.now().isoformat()}
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving API key: {e}")
