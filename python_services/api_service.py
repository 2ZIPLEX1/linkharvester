# api_service.py
import os
import logging
import requests
import json
import time
from typing import Dict, List, Tuple, Any

# Configure logging 
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(root_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(logs_dir, 'api_service.log'),
    filemode='a'
)

def ensure_logs_directory():
    """Ensure the logs directory exists."""
    # Go up one level to place logs in root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(root_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

class APIService:
    """
    Service to handle communication with the Link Harvester API endpoint.
    Manages sending Steam IDs and handling responses.
    """
    
    def __init__(self, config_path: str = "../config.json"):
        """
        Initialize the API service.
        
        Args:
            config_path: Path to the configuration file with API key and username
        """
        self.config_path = config_path
        self.filtered_file = os.path.join("..", "steam_data", "filtered_steamids.txt")
        self.api_key = None
        self.username = None
        self.api_endpoint = "https://ziplex2.pythonanywhere.com/links/api/add-link/"
        
        # Ensure necessary directories exist
        os.makedirs(os.path.join("..", "steam_data"), exist_ok=True)
        
        # Load configuration
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load API key and username from configuration file.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.config_path):
                # Create default configuration file if it doesn't exist
                default_config = {
                    "tradebot_api_key": "",
                    "steam_api_key": "",
                    "username": ""
                }
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logging.warning(f"Created default configuration file at {self.config_path}")
                logging.warning("Please update with valid API key and username")
                return False
                
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            self.api_key = config.get("tradebot_api_key", "")
            self.username = config.get("username", "")
            
            if not self.api_key or not self.username:
                logging.error("API key or username not found in configuration")
                return False
                
            logging.info(f"Configuration loaded successfully. Username: {self.username}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            return False
    
    def save_to_fallback_file(self, steam_id: str) -> bool:
        """
        Save a Steam ID to the fallback file for later processing.
        
        Args:
            steam_id: Steam ID to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if the ID is already in the file
            existing_ids = []
            if os.path.exists(self.filtered_file):
                with open(self.filtered_file, 'r') as f:
                    existing_ids = [line.strip() for line in f.readlines()]
            
            # Only add if not already present
            if steam_id not in existing_ids:
                with open(self.filtered_file, 'a') as f:
                    f.write(f"{steam_id}\n")
                logging.info(f"Saved Steam ID {steam_id} to fallback file")
                
            return True
            
        except Exception as e:
            logging.error(f"Error saving to fallback file: {e}")
            return False
    
    def read_fallback_file(self) -> List[str]:
        """
        Read the list of Steam IDs from the fallback file.
        
        Returns:
            List[str]: List of Steam IDs
        """
        try:
            if not os.path.exists(self.filtered_file):
                return []
                
            with open(self.filtered_file, 'r') as f:
                # Read lines and strip whitespace
                ids = [line.strip() for line in f.readlines()]
                
            # Filter out empty lines
            ids = [id for id in ids if id]
            logging.info(f"Read {len(ids)} Steam IDs from fallback file")
            return ids
            
        except Exception as e:
            logging.error(f"Error reading fallback file: {e}")
            return []
    
    def update_fallback_file(self, ids: List[str]) -> bool:
        """
        Update the fallback file with the given list of Steam IDs.
        
        Args:
            ids: List of Steam IDs to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.filtered_file, 'w') as f:
                for id in ids:
                    f.write(f"{id}\n")
                    
            logging.info(f"Updated fallback file with {len(ids)} Steam IDs")
            return True
            
        except Exception as e:
            logging.error(f"Error updating fallback file: {e}")
            return False
    
    def remove_from_fallback_file(self, steam_id: str) -> bool:
        """
        Remove a single Steam ID from the fallback file.
        
        Args:
            steam_id: Steam ID to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read existing IDs
            ids = self.read_fallback_file()
            
            # Remove the ID if it exists
            if steam_id in ids:
                ids.remove(steam_id)
                logging.info(f"Removed Steam ID {steam_id} from fallback file")
                return self.update_fallback_file(ids)
            
            return True
                
        except Exception as e:
            logging.error(f"Error removing from fallback file: {e}")
            return False
    
    def send_steam_id_to_api(self, steam_id: str) -> Tuple[bool, dict]:
        """
        Send a single Steam ID to the API endpoint.
        
        Args:
            steam_id: Steam ID to send
            
        Returns:
            Tuple[bool, dict]: (Success status, Response data or error message)
        """
        try:
            # Ensure we have valid configuration
            if not self.api_key or not self.username:
                error_msg = "Missing API key or username in configuration"
                logging.error(error_msg)
                return False, {"error": error_msg}
            
            # Prepare request
            params = {
                "steam_id": steam_id,
                "username": self.username,
                "api_key": self.api_key
            }
            
            # Send request
            logging.info(f"Sending Steam ID {steam_id} to API endpoint")
            response = requests.get(self.api_endpoint, params=params, timeout=10)
            
            # Get response data
            try:
                data = response.json()
            except ValueError:
                data = {"error": "Invalid JSON response", "status_code": response.status_code}
            
            # Log response
            log_msg = f"API response for {steam_id}: Status {response.status_code}"
            if response.status_code == 200:
                logging.info(f"{log_msg}, Success")
                return True, data
            else:
                logging.warning(f"{log_msg}, {data.get('error', 'Unknown error')}")
                return False, data
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logging.error(error_msg)
            return False, {"error": error_msg, "exception": "RequestException"}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg)
            return False, {"error": error_msg}
    
    def handle_new_steam_id(self, steam_id: str) -> Dict[str, Any]:
        """
        Primary function to handle a newly discovered Steam ID.
        Attempts to send it to the API directly and only falls back to
        saving to file if the API call fails. If successful, also tries
        to process any previously saved IDs.
        
        Args:
            steam_id: Steam ID to process
            
        Returns:
            Dict: Result of the operation
        """
        result = {
            "steam_id": steam_id,
            "success": False,
            "saved_to_fallback": False,
            "fallback_processed": False,
            "fallback_results": None,
            "error": None
        }
        
        try:
            # First, try to send directly to API
            success, response = self.send_steam_id_to_api(steam_id)
            
            if success:
                # Successful API call
                result["success"] = True
                logging.info(f"Successfully added Steam ID {steam_id} to link harvester")
                
                # Since API is working, try to process any previously saved IDs
                fallback_ids = self.read_fallback_file()
                if fallback_ids:
                    logging.info(f"API is working, attempting to process {len(fallback_ids)} saved IDs")
                    result["fallback_processed"] = True
                    result["fallback_results"] = self.process_fallback_file()
                
                return result
                
            # Handle different error types
            error_type = response.get("error", "Unknown error")
            result["error"] = error_type
            
            if "Link already exists" in error_type:
                # Link already exists - consider this a success, no need to save
                logging.info(f"Link already exists for Steam ID {steam_id}")
                result["success"] = True
                
                # Since API is working, try to process any previously saved IDs
                fallback_ids = self.read_fallback_file()
                if fallback_ids:
                    logging.info(f"API is working, attempting to process {len(fallback_ids)} saved IDs")
                    result["fallback_processed"] = True
                    result["fallback_results"] = self.process_fallback_file()
                
                return result
                
            elif "Invalid Steam ID format" in error_type:
                # Invalid Steam ID format - don't save this ID
                logging.warning(f"Invalid Steam ID format: {steam_id}")
                return result
                
            else:
                # Other errors - save to fallback file
                logging.warning(f"API call failed for {steam_id}: {error_type}. Saving to fallback file.")
                result["saved_to_fallback"] = self.save_to_fallback_file(steam_id)
                return result
                
        except Exception as e:
            # Unexpected error - save to fallback file
            error_msg = f"Unexpected error processing {steam_id}: {e}"
            logging.error(error_msg)
            result["error"] = error_msg
            result["saved_to_fallback"] = self.save_to_fallback_file(steam_id)
            return result
    
    def process_fallback_file(self) -> Dict[str, Any]:
        """
        Process all Steam IDs saved in the fallback file.
        Attempts to send each ID to the API and removes from file if successful.
        
        Returns:
            Dict: Summary of processing results
        """
        start_time = time.time()
        results = {
            "total": 0,
            "success": 0,
            "error": 0,
            "skipped": 0,
            "remaining": 0,
            "errors": []
        }
        
        # Ensure configuration is loaded
        if not self.load_config():
            error_msg = "Failed to load configuration"
            logging.error(error_msg)
            results["errors"].append(error_msg)
            return results
        
        # Read all IDs from fallback file
        ids = self.read_fallback_file()
        results["total"] = len(ids)
        
        if not ids:
            logging.info("No Steam IDs found in fallback file")
            return results
        
        logging.info(f"Starting to process {len(ids)} Steam IDs from fallback file")
        
        # List to track IDs to keep (those that failed due to API unavailable)
        ids_to_keep = []
        
        # Process each ID
        for steam_id in ids:
            try:
                success, response = self.send_steam_id_to_api(steam_id)
                
                if success:
                    # Successful API call - don't keep this ID
                    results["success"] += 1
                    logging.info(f"Successfully added Steam ID {steam_id} from fallback file")
                    
                else:
                    # Handle different error types
                    error_type = response.get("error", "Unknown error")
                    
                    if "Invalid API key" in error_type:
                        # Invalid API key - stop processing and keep all remaining IDs
                        logging.error(f"Invalid API key detected. Stopping processing.")
                        results["errors"].append(f"Invalid API key: {error_type}")
                        ids_to_keep.extend(ids[ids.index(steam_id):])
                        break
                        
                    elif "User not found" in error_type:
                        # Invalid username - stop processing and keep all remaining IDs
                        logging.error(f"Invalid username detected: {error_type}")
                        results["errors"].append(f"Invalid username: {error_type}")
                        ids_to_keep.extend(ids[ids.index(steam_id):])
                        break
                        
                    elif "RequestException" in response.get("exception", ""):
                        # API unavailable - keep this ID for later and stop processing
                        logging.warning(f"API appears to be unavailable. Keeping ID {steam_id} and remaining IDs for later.")
                        results["errors"].append(f"API unavailable: {error_type}")
                        ids_to_keep.extend(ids[ids.index(steam_id):])
                        results["error"] += len(ids) - ids.index(steam_id)
                        break
                        
                    elif "Link already exists" in error_type:
                        # Link already exists - don't keep this ID
                        logging.info(f"Link already exists for Steam ID {steam_id}")
                        results["skipped"] += 1
                        
                    elif "Invalid Steam ID format" in error_type:
                        # Invalid Steam ID format - don't keep this ID
                        logging.warning(f"Invalid Steam ID format: {steam_id}")
                        results["skipped"] += 1
                        
                    else:
                        # Other error - keep this ID but continue processing others
                        logging.warning(f"Unknown error for {steam_id}: {error_type}")
                        ids_to_keep.append(steam_id)
                        results["error"] += 1
                
            except Exception as e:
                # Unexpected error - keep this ID but continue processing others
                logging.error(f"Unexpected error processing {steam_id}: {e}")
                ids_to_keep.append(steam_id)
                results["error"] += 1
        
        # Update fallback file with IDs that need to be kept
        if ids != ids_to_keep:  # Only write if there's a change
            if ids_to_keep:
                logging.info(f"Updating fallback file with {len(ids_to_keep)} remaining IDs")
                self.update_fallback_file(ids_to_keep)
            else:
                # If no IDs need to be kept, clear the file
                logging.info("All IDs processed successfully, clearing fallback file")
                if os.path.exists(self.filtered_file):
                    self.update_fallback_file([])
        
        # Add remaining count to results
        results["remaining"] = len(ids_to_keep)
        
        # Add execution time to results
        results["execution_time"] = time.time() - start_time
        
        logging.info(f"Processing complete: {results['success']} successful, " 
                     f"{results['error']} errors, {results['skipped']} skipped, "
                     f"{results['remaining']} remaining")
        
        return results
    
    def send_notification(self, message_code: str) -> Tuple[bool, dict]:
        """
        Send a notification message to the API endpoint.
        
        Args:
            message_code: Code representing the message type (e.g., 'script-finished-running')
            
        Returns:
            Tuple[bool, dict]: (Success status, Response data or error message)
        """
        try:
            # Ensure we have valid configuration
            if not self.api_key or not self.username:
                error_msg = "Missing API key or username in configuration"
                logging.error(error_msg)
                return False, {"error": error_msg}
            
            # Prepare request
            params = {
                "username": self.username,
                "message_code": message_code,
                "api_key": self.api_key
            }
            
            # Define notification endpoint
            notification_endpoint = "https://ziplex2.pythonanywhere.com/en/links/api/message-from-linkharvester/"
            
            # Send request
            logging.info(f"Sending notification with message code: {message_code}")
            response = requests.get(notification_endpoint, params=params, timeout=10)
            
            # Get response data
            try:
                data = response.json()
            except ValueError:
                data = {"error": "Invalid JSON response", "status_code": response.status_code}
            
            # Log response
            log_msg = f"Notification API response: Status {response.status_code}"
            if response.status_code == 200:
                logging.info(f"{log_msg}, Success")
                return True, data
            else:
                logging.warning(f"{log_msg}, {data.get('error', 'Unknown error')}")
                return False, data
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error sending notification: {str(e)}"
            logging.error(error_msg)
            return False, {"error": error_msg, "exception": "RequestException"}
            
        except Exception as e:
            error_msg = f"Unexpected error sending notification: {str(e)}"
            logging.error(error_msg)
            return False, {"error": error_msg}

def main():
    """Main entry point when script is run directly"""
    logging.info("Starting API service")
    service = APIService()
    
    # Process any IDs in the fallback file
    results = service.process_fallback_file()
    
    print(f"\nProcessing results:")
    print(f"Total IDs: {results['total']}")
    print(f"Successfully processed: {results['success']}")
    print(f"Errors: {results['error']}")
    print(f"Skipped (already exists or invalid): {results['skipped']}")
    print(f"Remaining in fallback file: {results['remaining']}")
    print(f"Execution time: {results['execution_time']:.2f} seconds")
    
    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"- {error}")
        if len(results["errors"]) > 5:
            print(f"... and {len(results['errors']) - 5} more")
    
    # Test sending a new ID (uncomment to test)
    # test_id = "76561198340740317"
    # print(f"\nTesting with Steam ID: {test_id}")
    # test_result = service.handle_new_steam_id(test_id)
    # print(f"Result: {'Success' if test_result['success'] else 'Failed'}")
    # if test_result['saved_to_fallback']:
    #     print(f"Saved to fallback file for later processing")
    # if test_result['fallback_processed']:
    #     print(f"Also processed {test_result['fallback_results']['total']} IDs from fallback file")
    # if test_result['error']:
    #     print(f"Error: {test_result['error']}")

if __name__ == "__main__":
    main()