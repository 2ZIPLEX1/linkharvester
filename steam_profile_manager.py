# steam_profile_manager.py
import json
import os
import time
import logging
import urllib.request
from urllib.error import HTTPError
import threading
import traceback
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='steam_profile_manager.log',
    filemode='w'  # Changed from 'a' to 'w' to start fresh
)

# Replace with your actual API key
API_KEY = "MY_KEY_CENSORED"

class SteamProfileManager:
    def __init__(self, data_folder="steam_data"):
        self.data_folder = data_folder
        self.queue_file = os.path.join(data_folder, "profiles_queue.json")
        self.filtered_file = os.path.join(data_folder, "filtered_steamids.txt")
        self.profiles_queue = []
        self.processing_thread = None
        self.is_processing = False
        
        # Create data folder if it doesn't exist
        os.makedirs(data_folder, exist_ok=True)
        
        # Load existing queue
        self.load_queue()
        
    def load_queue(self):
        """Load the existing queue from file"""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r') as f:
                    self.profiles_queue = json.load(f)
                logging.info(f"Loaded {len(self.profiles_queue)} profiles from queue")
            except Exception as e:
                logging.error(f"Error loading queue: {e}")
                self.profiles_queue = []
        else:
            self.profiles_queue = []
    
    def save_queue(self):
        """Save the current queue to file"""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.profiles_queue, f, indent=2)
            logging.info(f"Saved {len(self.profiles_queue)} profiles to queue")
        except Exception as e:
            logging.error(f"Error saving queue: {e}")
    
    def add_profile_url(self, url):
        """Add a Steam profile URL to the processing queue"""
        try:
            # Extract vanity ID or Steam ID from URL
            vanity_id = None
            steam_id = None
            
            if "/id/" in url:
                vanity_id = url.split("/id/")[1].rstrip("/")
                logging.info(f"Extracted vanity ID: {vanity_id}")
            elif "/profiles/" in url:
                steam_id = url.split("/profiles/")[1].rstrip("/")
                logging.info(f"Extracted Steam ID: {steam_id}")
            else:
                logging.error(f"URL format not recognized: {url}")
                return False
            
            # Create profile object
            profile = {
                "url": url,
                "timestamp": time.time(),
                "vanity_id": vanity_id,
                "steam_id": steam_id,
                "checks": {
                    "animated_avatar": "to_check",
                    "avatar_frame": "to_check",
                    "mini_profile_background": "to_check",
                    "profile_background": "to_check",
                    "steam_level": "to_check",
                    "friends": "to_check"
                }
            }
            
            # Add to queue
            self.profiles_queue.append(profile)
            logging.info(f"Added profile to queue: {url}")
            
            # Save updated queue
            self.save_queue()
            
            # Start processing if not already running
            self.ensure_processing()
            
            return True
        except Exception as e:
            logging.error(f"Error adding profile to queue: {e}")
            return False
    
    def ensure_processing(self):
        """Ensure the background processing thread is running"""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(target=self.process_queue)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logging.info("Started background processing thread")
    
    def process_queue(self):
        """Process profiles in the queue"""
        if self.is_processing:
            logging.info("Processing already in progress, skipping")
            return
                
        self.is_processing = True
        
        try:
            logging.info(f"Starting queue processing with {len(self.profiles_queue)} profiles")
            max_profiles_to_process = 3  # Process at most 3 profiles per run to avoid long-running threads
            profiles_processed = 0
            
            # Add a counter to prevent infinite processing on a single profile
            profile_attempt_count = 0
            max_attempts_per_profile = 3
            
            while self.profiles_queue and profiles_processed < max_profiles_to_process:
                # Process most recently added profile first (from the end)
                profile = self.profiles_queue[-1]
                
                # Check if we've been stuck on this profile too many times
                profile_attempt_count += 1
                if profile_attempt_count > max_attempts_per_profile:
                    logging.warning(f"Max attempts reached for profile {profile['url']}, moving to beginning of queue")
                    # Move to beginning of queue
                    temp_profile = self.profiles_queue.pop()
                    self.profiles_queue.insert(0, temp_profile)
                    self.save_queue()
                    profile_attempt_count = 0  # Reset counter for next profile
                    continue
                
                logging.info(f"Processing profile {profiles_processed+1}/{max_profiles_to_process}: {profile['url']} (Queue length: {len(self.profiles_queue)}, Attempt: {profile_attempt_count})")
                
                # Log what we're about to do
                if not profile['steam_id'] and profile['vanity_id']:
                    logging.info(f"About to resolve vanity ID: {profile['vanity_id']}")
                elif profile['steam_id']:
                    logging.info(f"Profile already has Steam ID: {profile['steam_id']}")
                else:
                    logging.error(f"Profile has neither vanity_id nor steam_id: {profile}")
                    # Remove invalid profile
                    self.profiles_queue.pop()
                    self.save_queue()
                    continue
                
                # Step 1: Ensure we have a Steam ID
                if not profile['steam_id'] and profile['vanity_id']:
                    logging.info(f"Attempting to resolve vanity ID: {profile['vanity_id']}")
                    try:
                        result = self.resolve_vanity_url(profile['vanity_id'])
                        logging.info(f"Vanity URL resolution result: {result}")
                        
                        if result.get('success') and result.get('steamId'):
                            profile['steam_id'] = result['steamId']
                            logging.info(f"Resolved vanity URL to Steam ID: {profile['steam_id']}")
                            # Save queue after getting Steam ID
                            self.save_queue()
                        else:
                            # Failed to resolve, remove from queue
                            error_msg = result.get('error', 'Unknown error')
                            logging.error(f"Failed to resolve vanity URL: {profile['vanity_id']} - {error_msg}")
                            self.profiles_queue.pop()
                            self.save_queue()
                            profiles_processed += 1
                            profile_attempt_count = 0  # Reset for next profile
                            continue
                    except Exception as e:
                        logging.error(f"Exception resolving vanity URL: {e}")
                        logging.error(traceback.format_exc())
                        # Keep in queue but move to next profile
                        # Temporarily move this profile to the beginning of the queue so we don't keep retrying it
                        temp_profile = self.profiles_queue.pop()
                        self.profiles_queue.insert(0, temp_profile)
                        self.save_queue()
                        profiles_processed += 1
                        profile_attempt_count = 0  # Reset for next profile
                        continue
                
                # Step 2: Check for animated avatar
                if profile['steam_id'] and profile['checks']['animated_avatar'] == "to_check":
                    logging.info(f"Checking animated avatar for: {profile['steam_id']}")
                    try:
                        result = self.check_animated_avatar(profile['steam_id'])
                        logging.info(f"Animated avatar check result: {result}")
                        
                        if result.get('success'):
                            if result.get('passed'):
                                profile['checks']['animated_avatar'] = "passed"
                                logging.info(f"Profile passed animated avatar check: {profile['steam_id']}")
                                self.save_queue() # Save progress
                            else:
                                # Failed check, remove from queue
                                logging.info(f"Profile failed animated avatar check: {profile['steam_id']}")
                                self.profiles_queue.pop()
                                self.save_queue()
                                profiles_processed += 1
                                profile_attempt_count = 0  # Reset for next profile
                                continue
                        else:
                            # API error, log and try again later
                            error_msg = result.get('error', 'Unknown error')
                            logging.error(f"Error checking animated avatar: {error_msg}")
                            # Temporarily move this profile to the beginning of the queue
                            temp_profile = self.profiles_queue.pop()
                            self.profiles_queue.insert(0, temp_profile)
                            self.save_queue()
                            profiles_processed += 1
                            profile_attempt_count = 0  # Reset for next profile
                            time.sleep(2)  # Add delay before next profile
                            continue
                    except Exception as e:
                        logging.error(f"Exception checking animated avatar: {e}")
                        logging.error(traceback.format_exc())
                        # Temporarily move this profile to the beginning of the queue
                        temp_profile = self.profiles_queue.pop()
                        self.profiles_queue.insert(0, temp_profile)
                        self.save_queue()
                        profiles_processed += 1
                        profile_attempt_count = 0  # Reset for next profile
                        time.sleep(2)  # Add delay before next profile
                        continue
                
                # TODO: Implement additional checks here
                # For now, if it reaches here and passes animated avatar check, consider it fully passed
                
                # Check if all implemented checks are passed
                all_checks_passed = True
                for check_name, check_status in profile['checks'].items():
                    # Only consider checks that we've actually implemented
                    if check_name == 'animated_avatar':
                        if check_status != "passed":
                            all_checks_passed = False
                            break
                
                if all_checks_passed:
                    logging.info(f"Profile passed all checks: {profile['steam_id']}")
                    
                    # Remove from queue
                    self.profiles_queue.pop()
                    
                    # Save to filtered list
                    save_result = self.save_to_filtered_list(profile['steam_id'])
                    logging.info(f"Save to filtered list result: {save_result}")
                    
                    # Save updated queue
                    self.save_queue()
                else:
                    logging.warning(f"Not all checks passed for profile: {profile['steam_id']}")
                    # Move to beginning of queue to avoid infinite processing
                    temp_profile = self.profiles_queue.pop()
                    self.profiles_queue.insert(0, temp_profile)
                    self.save_queue()
                
                # Increment counter and reset attempt count
                profiles_processed += 1
                profile_attempt_count = 0
                
                # Small delay between processing
                time.sleep(1)
            
            # If we processed the maximum number but there are still profiles in the queue
            if self.profiles_queue:
                logging.info(f"Processed maximum number of profiles ({max_profiles_to_process}), {len(self.profiles_queue)} profiles remaining in queue")
                
            logging.info(f"Queue processing complete for this run, processed {profiles_processed} profiles")
            
        except Exception as e:
            logging.error(f"Error in queue processing: {e}")
            logging.error(traceback.format_exc())
        finally:
            self.is_processing = False

    def resolve_vanity_url(self, vanity_id):
        """Resolve a vanity URL to a Steam ID"""
        try:
            url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={API_KEY}&vanityurl={vanity_id}"
            logging.info(f"Calling vanity URL resolution API: {url}")
            
            # Create a request with timeout (5 seconds)
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            
            logging.info("API request completed successfully, reading response")
            data = response.read().decode('utf-8')
            logging.info(f"API response received ({len(data)} bytes)")
            
            # Parse JSON response
            try:
                json_data = json.loads(data)
                logging.info("JSON parsing successful")
            except json.JSONDecodeError as je:
                logging.error(f"JSON decode error: {je}")
                logging.error(f"Raw response data: {data[:200]}...")  # Log first 200 chars
                return {"success": False, "error": f"Invalid JSON response: {je}"}
            
            if 'response' in json_data and 'success' in json_data['response']:
                if json_data['response']['success'] == 1:
                    steam_id = json_data['response']['steamid']
                    logging.info(f"Successfully resolved to Steam ID: {steam_id}")
                    return {"success": True, "steamId": steam_id}
                else:
                    logging.warning(f"API returned unsuccessful response: {json_data}")
                    return {"success": False, "error": "Could not resolve vanity URL", "data": json_data}
            else:
                logging.error(f"Unexpected API response format: {json_data}")
                return {"success": False, "error": "Unexpected API response format", "data": json_data}
                
        except urllib.error.URLError as e:
            logging.error(f"URL Error in resolve_vanity_url: {e.reason}")
            return {"success": False, "error": f"URL Error: {e.reason}"}
        except urllib.error.HTTPError as e:
            logging.error(f"HTTP Error in resolve_vanity_url: {e.code} - {e.reason}")
            return {"success": False, "error": f"HTTP Error: {e.code} - {e.reason}"}
        except socket.timeout:
            logging.error("Socket timeout while resolving vanity URL")
            return {"success": False, "error": "API call timed out (socket)"}
        except TimeoutError:
            logging.error("Timeout error while resolving vanity URL")
            return {"success": False, "error": "API call timed out"}
        except Exception as e:
            logging.error(f"Exception in resolve_vanity_url: {str(e)}")
            logging.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def check_animated_avatar(self, steam_id):
        """Check if a Steam profile has an animated avatar"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetAnimatedAvatar/v1/?steamid={steam_id}"
            logging.info(f"Calling animated avatar API: {url}")
            
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            logging.info(f"Raw API response: {data}")
            
            if 'response' in data and 'avatar' in data['response']:
                has_animated_avatar = len(data['response']['avatar']) > 0
                
                return {
                    "success": True,
                    "passed": not has_animated_avatar,
                    "details": data['response'] if has_animated_avatar else {}
                }
            else:
                return {"success": False, "error": "Unexpected API response format", "data": data}
        except HTTPError as e:
            logging.error(f"HTTP Error in check_animated_avatar: {e.code} - {e.reason}")
            return {"success": False, "error": f"HTTP Error: {e.code} - {e.reason}"}
        except Exception as e:
            logging.error(f"Exception in check_animated_avatar: {str(e)}")
            logging.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def save_to_filtered_list(self, steam_id):
        """Save a Steam ID to the filtered list"""
        try:
            with open(self.filtered_file, 'a') as f:
                f.write(f"{steam_id}\n")
            logging.info(f"Saved Steam ID to filtered list: {steam_id}")
            return True
        except Exception as e:
            logging.error(f"Error saving to filtered list: {e}")
            return False
    
    def get_queue_status(self):
        """Get current status of the queue"""
        return {
            "queue_length": len(self.profiles_queue),
            "is_processing": self.is_processing,
            "profiles": self.profiles_queue
        }
    
    def process_profiles_now(self):
        """Manually trigger queue processing"""
        self.is_processing = False  # Reset in case it got stuck
        self.ensure_processing()
        return {"success": True, "message": "Processing triggered"}

# Test function
def test_manager():
    manager = SteamProfileManager()
    
    # First, let's reset the filtered file
    if os.path.exists(manager.filtered_file):
        os.remove(manager.filtered_file)
        print(f"Removed existing filtered file: {manager.filtered_file}")
    
    # Add test profiles
    test_urls = [
        "https://steamcommunity.com/id/MISTER_GTX/",
        "https://steamcommunity.com/profiles/76561198840867172/",
        "https://steamcommunity.com/id/invalid_user_test/"
    ]
    
    for url in test_urls:
        print(f"Adding URL to queue: {url}")
        manager.add_profile_url(url)
    
    # Wait for processing to complete
    print("Waiting for processing to complete...")
    while manager.is_processing or len(manager.profiles_queue) > 0:
        status = manager.get_queue_status()
        print(f"Queue length: {status['queue_length']}, Processing: {status['is_processing']}")
        time.sleep(2)
    
    print("Processing complete!")
    
    # Check the filtered list
    if os.path.exists(manager.filtered_file):
        with open(manager.filtered_file, 'r') as f:
            filtered_ids = f.read().splitlines()
        print(f"Filtered Steam IDs ({len(filtered_ids)} total): {filtered_ids}")
        
        # Check for duplicates
        unique_ids = set(filtered_ids)
        print(f"Unique Steam IDs ({len(unique_ids)} total): {list(unique_ids)}")
        
        if len(filtered_ids) != len(unique_ids):
            print(f"WARNING: Found {len(filtered_ids) - len(unique_ids)} duplicate entries!")
    else:
        print("No filtered Steam IDs found")

# Run if executed directly
if __name__ == "__main__":
    test_manager()