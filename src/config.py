import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data', 'config.json')

DEFAULT_CONFIG = {
    "window": {
        "x": 50,
        "y": 50,
        "width": 400,
        "height": 600
    },
    "notes": "",
    "version": "1.0.0"
}

class ConfigManager:
    @staticmethod
    def load_config():
        """Load config from disk or return default."""
        if not os.path.exists(os.path.dirname(CONFIG_FILE)):
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return {**DEFAULT_CONFIG, **json.load(f)} # Merge with defaults
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG
        return DEFAULT_CONFIG

    @staticmethod
    def save_config(data):
        """Save config to disk."""
        try:
            # Ensure proper structure merging
            current = ConfigManager.load_config()
            current.update(data)
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(current, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
