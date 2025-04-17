import time
import glob
import os
import json
import logging

# Configure logging 
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(root_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)
LOG_FILE = os.path.join(logs_dir, 'image_recognition.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

def ensure_logs_directory():
    """Ensure the logs directory exists."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(root_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def load_config():
    """Load configuration from config.json"""
    try:
        # Path to config.json in the root directory
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        
        # Check if file exists
        if not os.path.exists(config_path):
            logging.warning(f"Config file not found at: {config_path}, using defaults")
            return {}
            
        # Load JSON config
        with open(config_path, 'r') as f:
            config = json.load(f)
            logging.info(f"Loaded configuration from {config_path}")
            return config
    except Exception as e:
        logging.error(f"Error loading config.json: {str(e)}")
        return {}

def get_latest_screenshot(screenshot_path=None):
    """Get the most recent screenshot from Steam's screenshot folder"""
    try:
        # Get Steam user ID from environment or use default
        import os
        steam_user_id = os.environ.get("STEAM_USER_ID", "1249018443")
        
        # Construct the path using the user ID
        STEAM_SCREENSHOTS_PATH = f"C:\\Program Files (x86)\\Steam\\userdata\\{steam_user_id}\\760\\remote\\730\\screenshots"
        
        screenshots = glob.glob(os.path.join(STEAM_SCREENSHOTS_PATH, '*.jpg'))
        
        if not screenshots:
            logging.warning("No screenshots found")
            return None
            
        latest_screenshot = max(screenshots, key=os.path.getmtime)
        
        # Only use if it's less than 5 seconds old
        if time.time() - os.path.getmtime(latest_screenshot) > 30:
            logging.warning("No recent screenshots found")
            return None
            
        return latest_screenshot
    except Exception as e:
        logging.error(f"Error getting screenshot: {str(e)}")
        return None