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
    filemode='a'
)

# Replace with your actual API key
API_KEY = "CFBC4A70290D1647D771A3016F59EAC7"

class _CheckHandlers:
    """Static methods for handling specific check types"""
    
    @staticmethod
    def animated_avatar(manager, steam_id):
        """Handle animated avatar check"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetAnimatedAvatar/v1/?steamid={steam_id}"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data and 'avatar' in data['response']:
                has_animated_avatar = len(data['response']['avatar']) > 0
                return {
                    "success": True,
                    "passed": not has_animated_avatar,
                    "details": data['response'] if has_animated_avatar else {}
                }
            return {"success": False, "error": "Unexpected API response"}
            
        except Exception as e:
            manager._log_check_error("animated_avatar", steam_id, e)
            return {"success": False, "error": str(e)}

    @staticmethod
    def avatar_frame(manager, steam_id):
        """Handle avatar frame check"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetAvatarFrame/v1/?steamid={steam_id}"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data and 'avatar_frame' in data['response']:
                has_frame = bool(data['response']['avatar_frame'])
                return {
                    "success": True,
                    "passed": not has_frame,
                    "details": data['response'] if has_frame else {}
                }
            return {"success": False, "error": "Unexpected API response"}
            
        except Exception as e:
            manager._log_check_error("avatar_frame", steam_id, e)
            return {"success": False, "error": str(e)}
        
    @staticmethod
    def mini_profile_background(manager, steam_id):
        """Handle mini profile background check"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetMiniProfileBackground/v1/?steamid={steam_id}"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data and 'profile_background' in data['response']:
                has_background = bool(data['response']['profile_background'])
                return {
                    "success": True,
                    "passed": not has_background,
                    "details": data['response'] if has_background else {}
                }
            return {"success": False, "error": "Unexpected API response"}
            
        except Exception as e:
            manager._log_check_error("mini_profile_background", steam_id, e)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def profile_background(manager, steam_id):
        """Handle profile background check"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetProfileBackground/v1/?steamid={steam_id}"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data and 'profile_background' in data['response']:
                has_background = bool(data['response']['profile_background'])
                return {
                    "success": True,
                    "passed": not has_background,
                    "details": data['response'] if has_background else {}
                }
            return {"success": False, "error": "Unexpected API response"}
            
        except Exception as e:
            manager._log_check_error("profile_background", steam_id, e)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def steam_level(manager, steam_id):
        """Handle Steam level check (passes if level <= 13)"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key={API_KEY}&steamid={steam_id}"
            logging.info(f"Checking Steam level for {steam_id}")
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data:
                # If response is empty, consider it a pass
                if not data['response']:
                    logging.info(f"Steam level check for {steam_id}: Empty response - automatically passing")
                    return {
                        "success": True,
                        "passed": True,
                        "details": {"note": "Empty response from API"},
                        "level": 0
                    }
                
                # Regular case - response contains player_level
                if 'player_level' in data['response']:
                    player_level = data['response']['player_level']
                    logging.info(f"Steam level check for {steam_id}: Level {player_level} (Max allowed: 14)")
                    return {
                        "success": True,
                        "passed": player_level <= 13,
                        "details": {"player_level": player_level},
                        "level": player_level
                    }
                    
            logging.error(f"Unexpected API response format for Steam level check: {data}")
            return {"success": False, "error": "Unexpected API response"}
            
        except Exception as e:
            manager._log_check_error("steam_level", steam_id, e)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def friends(manager, steam_id):
        """Handle friends count check (passes if <= 60 friends)"""
        try:
            url = f"https://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={API_KEY}&steamid={steam_id}&relationship=friend"
            logging.info(f"Checking friends count for {steam_id}")
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'friendslist' in data and 'friends' in data['friendslist']:
                friends_count = len(data['friendslist']['friends'])
                logging.info(f"Friends check for {steam_id}: {friends_count} friends (Max allowed: 60)")
                return {
                    "success": True,
                    "passed": friends_count <= 60,
                    "details": {
                        "friends_count": friends_count,
                        "sample_friends": data['friendslist']['friends'][:3]
                    },
                    "count": friends_count
                }
                
            logging.error(f"Unexpected API response format for friends check: {data}")
            return {"success": False, "error": "Unexpected API response"}
            
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logging.info(f"Friends check for {steam_id}: Private profile - automatically passing")
                return {
                    "success": True,
                    "passed": True,
                    "details": {"error": "Private profile - cannot check friends"},
                    "count": 0
                }
            manager._log_check_error("friends", steam_id, e)
            return {"success": False, "error": str(e)}
        except Exception as e:
            manager._log_check_error("friends", steam_id, e)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def csgo_inventory(manager, steam_id):
        """Check if user has CS:GO inventory (passes if empty/null)"""
        try:
            url = f"https://steamcommunity.com/inventory/{steam_id}/730/2"
            logging.info(f"Checking CS:GO inventory for {steam_id}")
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            
            # Pass if response is null or empty
            if data is None or not data:
                logging.info(f"CS:GO inventory check passed for {steam_id} (empty)")
                return {
                    "success": True,
                    "passed": True,
                    "details": {}
                }
            
            # Check if inventory is actually empty
            if isinstance(data, dict) and not data.get('assets', []) and not data.get('descriptions', []):
                logging.info(f"CS:GO inventory check passed for {steam_id} (empty structure)")
                return {
                    "success": True,
                    "passed": True,
                    "details": {}
                }
            
            # Inventory exists
            item_count = len(data.get('assets', [])) if isinstance(data, dict) else 0
            logging.info(f"CS:GO inventory check failed for {steam_id} (found {item_count} items)")
            return {
                "success": True,
                "passed": False,
                "details": {
                    "item_count": item_count,
                    "sample_items": data.get('assets', [])[:3] if isinstance(data, dict) else []
                }
            }
            
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Private inventory - treat as passed
                logging.info(f"CS:GO inventory check for {steam_id}: Private inventory - automatically passing")
                return {
                    "success": True,
                    "passed": True,
                    "details": {"error": "Private inventory - cannot check"}
                }
            manager._log_check_error("csgo_inventory", steam_id, e)
            return {"success": False, "error": str(e)}
        except Exception as e:
            manager._log_check_error("csgo_inventory", steam_id, e)
            return {"success": False, "error": str(e)}

class _CheckConfig:
    """Configuration for all supported checks"""
    
    CHECKS = {
        'animated_avatar': {
            'handler': _CheckHandlers.animated_avatar,
            'empty_means_pass': True,
            'description': 'Checks for animated profile avatars'
        },
        'avatar_frame': {
            'handler': _CheckHandlers.avatar_frame,
            'empty_means_pass': True,
            'description': 'Checks for profile avatar frames'
        },
        'mini_profile_background': {
            'handler': _CheckHandlers.mini_profile_background,
            'empty_means_pass': True,
            'description': 'Checks for mini profile backgrounds'
        },
        'profile_background': {
            'handler': _CheckHandlers.profile_background,
            'empty_means_pass': True,
            'description': 'Checks for profile backgrounds'
        },
        'steam_level': {
            'handler': _CheckHandlers.steam_level,
            'empty_means_pass': False,  # This check doesn't use empty means pass
            'description': 'Checks if Steam level is 13 or lower'
        },
        'friends': {
            'handler': _CheckHandlers.friends,
            'empty_means_pass': False,
            'description': 'Checks if user has 60 or fewer friends'
        },
        'csgo_inventory': {
            'handler': _CheckHandlers.csgo_inventory,
            'empty_means_pass': True,
            'description': 'Checks for CS:GO inventory (passes if empty)'
        }
        # New checks can be added here
    }

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
    
    def _log_check_error(self, check_name, steam_id, error):
        """Centralized error logging for checks"""
        logging.error(f"Check '{check_name}' failed for {steam_id}: {error}")
        logging.error(traceback.format_exc())
        
    def _process_single_check(self, profile, check_name):
        """Generic check processor"""
        if check_name not in _CheckConfig.CHECKS:
            logging.warning(f"Unknown check type: {check_name}")
            return None
            
        handler = _CheckConfig.CHECKS[check_name]['handler']
        return handler(self, profile['steam_id'])

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
                    "friends": "to_check",
                    "csgo_inventory": "to_check"
                }
            }
            
            # Add to queue
            self.profiles_queue.append(profile)
            logging.info(f"Added profile to queue: {url}")
            
            # Save updated queue
            self.save_queue()
            
            # Don't start background processing - we'll do it synchronously
            # self.ensure_processing()
            
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
            
            # Counter to track profiles processed
            profiles_processed = 0
            profiles_completed = 0
            profiles_failed = 0
            
            # Process each profile in the queue
            index = len(self.profiles_queue) - 1
            while index >= 0:
                if index >= len(self.profiles_queue):
                    index = len(self.profiles_queue) - 1
                    if index < 0:
                        break
                        
                profile = self.profiles_queue[index]
                
                logging.info(f"Processing profile: {profile['url']} (Queue position: {index+1}/{len(self.profiles_queue)})")
                profiles_processed += 1
                
                # STEP 1: Ensure we have a Steam ID
                if not profile['steam_id'] and profile['vanity_id']:
                    logging.info(f"About to resolve vanity ID: {profile['vanity_id']}")
                    try:
                        result = self.resolve_vanity_url(profile['vanity_id'])
                        logging.info(f"Vanity URL resolution result: {result}")
                        
                        if result.get('success') and result.get('steamId'):
                            profile['steam_id'] = result['steamId']
                            logging.info(f"Resolved vanity URL to Steam ID: {profile['steam_id']}")
                            # Save queue after getting Steam ID
                            self.save_queue()
                            # Continue processing this profile
                        else:
                            # Failed to resolve, remove from queue
                            error_msg = result.get('error', 'Unknown error')
                            logging.error(f"Failed to resolve vanity URL: {profile['vanity_id']} - {error_msg}")
                            del self.profiles_queue[index]
                            self.save_queue()
                            profiles_failed += 1
                            index -= 1
                            continue
                    except Exception as e:
                        logging.error(f"Exception resolving vanity URL: {e}")
                        logging.error(traceback.format_exc())
                        # Move to next profile for now, we'll retry this one later
                        index -= 1
                        continue
                
                # STEP 2: Process each check for this profile
                all_checks_complete = True
                all_checks_passed = True
                
                for check_name, check_status in profile['checks'].items():
                    if check_status == "to_check":
                        result = self._process_single_check(profile, check_name)
                        
                        if not result:
                            continue  # Unknown check type
                            
                        if result.get('success'):
                            if result.get('passed'):
                                profile['checks'][check_name] = "passed"
                                self.save_queue()
                            else:
                                # Check failed - remove from queue
                                logging.info(f"Check failed for {profile['steam_id']}: {check_name}")
                                del self.profiles_queue[index]
                                self.save_queue()
                                profiles_failed += 1
                                all_checks_complete = False
                                break
                        else:
                            # API error - skip for now
                            logging.error(f"API error in check {check_name} for {profile['steam_id']}")
                            all_checks_complete = False
                            break
                    
                    # Track if any check isn't passed (even if not "to_check")
                    if profile['checks'][check_name] != "passed":
                        all_checks_passed = False
                
                # Only proceed if all checks were processed without errors
                if all_checks_complete:
                    # If all checks passed, add to filtered list and remove from queue
                    if all_checks_passed:
                        logging.info(f"All checks passed for profile: {profile['steam_id']}")
                        save_result = self.save_to_filtered_list(profile['steam_id'])
                        logging.info(f"Save to filtered list result: {save_result}")
                        
                        # Remove from queue
                        if index < len(self.profiles_queue):
                            del self.profiles_queue[index]
                            self.save_queue()
                            profiles_completed += 1
                
                # Move to next profile
                index -= 1
            
            # Final log message
            logging.info(f"Queue processing complete: {profiles_processed} profiles processed")
            logging.info(f"{profiles_completed} completed successfully, {profiles_failed} failed checks")
            logging.info(f"{len(self.profiles_queue)} profiles remaining in queue")
            
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
    
    def check_avatar_frame(self, steam_id):
        """Check if a Steam profile has an avatar frame"""
        try:
            url = f"https://api.steampowered.com/IPlayerService/GetAvatarFrame/v1/?steamid={steam_id}"
            logging.info(f"Calling avatar frame API: {url}")
            
            # Create a request with timeout (5 seconds)
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=5)
            
            data = json.loads(response.read().decode('utf-8'))
            
            if 'response' in data and 'avatar_frame' in data['response']:
                has_avatar_frame = bool(data['response']['avatar_frame'])
                
                return {
                    "success": True,
                    "passed": not has_avatar_frame,
                    "details": data['response'] if has_avatar_frame else {}
                }
            else:
                return {"success": False, "error": "Unexpected API response format", "data": data}
        except HTTPError as e:
            logging.error(f"HTTP Error in check_avatar_frame: {e.code} - {e.reason}")
            return {"success": False, "error": f"HTTP Error: {e.code} - {e.reason}"}
        except socket.timeout:
            logging.error("Socket timeout while checking avatar frame")
            return {"success": False, "error": "API call timed out (socket)"}
        except TimeoutError:
            logging.error("Timeout error while checking avatar frame")
            return {"success": False, "error": "API call timed out"}
        except Exception as e:
            logging.error(f"Exception in check_avatar_frame: {str(e)}")
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
        """Manually trigger queue processing synchronously"""
        self.is_processing = False  # Reset in case it got stuck
        logging.info("Running process_queue synchronously")
        self.process_queue()  # Run directly, not in a thread
        return {"success": True, "message": "Processing completed"}

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