# steam_bridge.py
import sys
import json
import logging
from steam_profile_manager import SteamProfileManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='steam_bridge.log',
    filemode='a'
)

def add_url(url):
    """Add a URL to the processing queue"""
    try:
        manager = SteamProfileManager()
        result = manager.add_profile_url(url)
        
        return {
            "success": result,
            "queue_length": len(manager.profiles_queue)
        }
    except Exception as e:
        logging.error(f"Error adding URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_status():
    """Get the current status of the processor"""
    try:
        manager = SteamProfileManager()
        return manager.get_queue_status()
    except Exception as e:
        logging.error(f"Error getting status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Command line interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python steam_bridge.py <command> [args]")
        print("Commands:")
        print("  add <url> - Add a URL to the processing queue")
        print("  status - Get current status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "add" and len(sys.argv) > 2:
        url = sys.argv[2]
        result = add_url(url)
        print(json.dumps(result))
    elif command == "status":
        result = get_status()
        print(json.dumps(result))
    elif command == "process":
        manager = SteamProfileManager()
        result = manager.process_profiles_now()
        print(json.dumps(result))
    else:
        print(json.dumps({"success": False, "error": "Unknown command"}))