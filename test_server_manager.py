import requests
import json
import subprocess
import os
import sys
import logging
import time
from datetime import datetime
from collections import deque
from api_service import APIService

# Setup logging to OneDrive Documents folder
home_dir = os.path.expanduser("~")
log_directory = "C:\\LinkHarvesterScript\logs"
os.makedirs(log_directory, exist_ok=True)
data_directory = "C:\\LinkHarvesterScript\\data"
os.makedirs(data_directory, exist_ok=True)

# Configure logging
log_file = os.path.join(log_directory, "cs2_test_server_manager.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='a'  # Append mode
)
logging.info("=== CS2 Test Server Manager Started ===")

class CS2TestServerManager:
    def __init__(self):
        self.api_url = "https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/?appid=730"
        self.servers_data = {}
        self.preferred_servers = []
        self.netsh_path = os.path.join(os.environ["SystemRoot"], "System32", "netsh.exe")
        self.ahk_script_path = os.path.join(os.getcwd(), "cs2_automation.ahk")
        
        # Set up data directories
        self.data_directory = data_directory
        self.preferred_servers_file = os.path.join(self.data_directory, "preferred_servers.txt")
        self.all_servers_file = os.path.join(self.data_directory, "all_servers.json")
        
        # Default timeout for AHK script execution (40 minutes in seconds)
        self.ahk_timeout = 40 * 60
        
        print(f"Preferred servers file: {self.preferred_servers_file}")
        logging.info(f"Preferred servers file: {self.preferred_servers_file}")
        
        # Load preferred servers if file exists
        self.load_preferred_servers()
        
    def load_preferred_servers(self):
        """Load preferred servers from file"""
        try:
            if os.path.exists(self.preferred_servers_file):
                with open(self.preferred_servers_file, 'r') as f:
                    self.preferred_servers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logging.info(f"Loaded {len(self.preferred_servers)} preferred servers")
                print(f"Loaded {len(self.preferred_servers)} preferred servers:")
                for server in self.preferred_servers:
                    print(f"  - {server}")
            else:
                logging.warning(f"Preferred servers file not found: {self.preferred_servers_file}")
                print(f"Preferred servers file not found: {self.preferred_servers_file}")
        except Exception as e:
            logging.error(f"Error loading preferred servers: {str(e)}")
            print(f"Error loading preferred servers: {str(e)}")
    
    def fetch_server_data(self):
        """Fetch server data from Steam API"""
        try:
            logging.info("Fetching server data from Steam API...")
            print("Fetching server data from Steam API...")
            response = requests.get(self.api_url)
            response.raise_for_status()
            data = response.json()
            
            # Process server data
            for server_code, server_info in data.get("pops", {}).items():
                server_name = server_info.get("desc", "Unknown") + f" ({server_code})"
                ip_addresses = []
                
                for relay in server_info.get("relays", []):
                    ip = relay.get("ipv4")
                    if ip:
                        ip_addresses.append(ip)
                
                if ip_addresses:
                    self.servers_data[server_name] = ",".join(ip_addresses)
            
            logging.info(f"Successfully fetched {len(self.servers_data)} servers")
            print(f"Successfully fetched {len(self.servers_data)} servers")
            
            # Save full server list for reference
            with open(self.all_servers_file, "w") as f:
                json.dump(self.servers_data, f, indent=4)
            
            return True
        except Exception as e:
            logging.error(f"Error fetching server data: {str(e)}")
            print(f"Error fetching server data: {str(e)}")
            return False
    
    def is_server_blocked(self, server_name):
        """Check if a server is blocked"""
        server_rule_name = f"CS2ServerPicker_{server_name.replace(' ', '')}"
        cmd = [self.netsh_path, "advfirewall", "firewall", "show", "rule", f"name={server_rule_name}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            return server_rule_name in result.stdout
        except Exception as e:
            logging.error(f"Error checking if server is blocked: {str(e)}")
            return False
    
    def block_server(self, server_name):
        """Block a specific server"""
        if self.is_server_blocked(server_name):
            logging.info(f"Server already blocked: {server_name}")
            return True
        
        if server_name not in self.servers_data:
            logging.error(f"Server not found in data: {server_name}")
            print(f"Server not found in data: {server_name}")
            return False
        
        server_rule_name = f"CS2ServerPicker_{server_name.replace(' ', '')}"
        cmd = [
            self.netsh_path, "advfirewall", "firewall", "add", "rule",
            f"name={server_rule_name}", "dir=out", "action=block", "protocol=ANY",
            f"remoteip={self.servers_data[server_name]}"
        ]
        
        try:
            logging.info(f"Blocking server: {server_name}")
            print(f"Blocking server: {server_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logging.error(f"Failed to block server: {result.stderr}")
                print(f"Failed to block server: {result.stderr}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error blocking server: {str(e)}")
            print(f"Error blocking server: {str(e)}")
            return False
    
    def unblock_server(self, server_name):
        """Unblock a specific server"""
        if not self.is_server_blocked(server_name):
            logging.info(f"Server not blocked: {server_name}")
            return True
        
        server_rule_name = f"CS2ServerPicker_{server_name.replace(' ', '')}"
        cmd = [
            self.netsh_path, "advfirewall", "firewall", "delete", "rule",
            f"name={server_rule_name}"
        ]
        
        try:
            logging.info(f"Unblocking server: {server_name}")
            print(f"Unblocking server: {server_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logging.error(f"Failed to unblock server: {result.stderr}")
                print(f"Failed to unblock server: {result.stderr}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error unblocking server: {str(e)}")
            print(f"Error unblocking server: {str(e)}")
            return False
    
    def block_all_servers(self):
        """Block all servers
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info("Blocking all servers")
            print("Blocking all servers")
            
            servers_blocked = 0
            for server_name in self.servers_data:
                if self.block_server(server_name):
                    servers_blocked += 1
            
            logging.info(f"Blocked {servers_blocked} servers")
            print(f"Blocked {servers_blocked} servers")
            
            return True
        except Exception as e:
            logging.error(f"Error in block_all_servers: {str(e)}")
            print(f"Error blocking servers: {str(e)}")
            return False
    
    def unblock_all_servers(self):
        """Unblock all servers"""
        logging.info("Unblocking all servers")
        print("Unblocking all servers")
        
        for server_name in self.servers_data:
            self.unblock_server(server_name)
        
        return True
    
    def block_all_but_one(self, target_server):
        """Block all servers except the specified one
        
        Args:
            target_server: The server name to keep unblocked
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if target_server not in self.servers_data:
                logging.error(f"Target server not found in data: {target_server}")
                print(f"Target server not found in data: {target_server}")
                return False
            
            logging.info(f"Blocking all servers except: {target_server}")
            print(f"Blocking all servers except: {target_server}")
            
            # First, unblock the target server if already blocked
            if self.is_server_blocked(target_server):
                self.unblock_server(target_server)
            
            # Block all other servers
            servers_blocked = 0
            for server_name in self.servers_data:
                if server_name != target_server:
                    if self.block_server(server_name):
                        servers_blocked += 1
            
            logging.info(f"Blocked {servers_blocked} servers, keeping {target_server} available")
            print(f"Blocked {servers_blocked} servers, keeping {target_server} available")
            
            return True
        except Exception as e:
            logging.error(f"Error in block_all_but_one: {str(e)}")
            print(f"Error blocking servers: {str(e)}")
            return False
    
    def run_ahk_script(self):
        """Run the AutoHotkey script and return the process object for monitoring
        
        Returns:
            subprocess.Popen: The process object for the AHK script
        """
        try:
            logging.info("Running AHK script")
            print("\nRunning AHK script to navigate CS2 UI...")
            print("The script will:")
            print("1. Click 'Play' button")
            print("2. Select Matchmaking mode")
            print("3. Select Casual league")
            print("4. Select Sigma match type")
            print("5. Accept/Start the match")
            print("6. View the player list (after a short delay)")
            print("\nMake sure CS2 is already running to avoid anti-cheat issues.")
            
            # Proceed without confirmation
            ahk_executable = "C:\\Program Files\\AutoHotkey\\v2\\AutoHotkey.exe"
            print("\nLaunching AHK script...")
            
            # Launch as a subprocess and return the process object
            process = subprocess.Popen(
                [ahk_executable, self.ahk_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            logging.info(f"AHK script started with PID: {process.pid}")
            print(f"AHK script started with PID: {process.pid}")
            
            return process
            
        except Exception as e:
            logging.error(f"Error running AHK script: {str(e)}")
            print(f"Error running AHK script: {str(e)}")
            return None
    
    def wait_for_ahk_completion(self, process):
        """Wait for the AHK script to complete with a timeout.
        This function also monitors the AHK log file for completion markers.
        
        Args:
            process: The subprocess.Popen object returned by run_ahk_script
            
        Returns:
            dict: Result information including:
                  - completed: Whether the process completed normally
                  - timeout: Whether a timeout occurred
                  - returncode: The process return code if completed
                  - elapsed_time: How long the process ran (in seconds)
        """
        if not process:
            return {
                "completed": False,
                "timeout": False,
                "returncode": None,
                "elapsed_time": 0,
                "error": "No process provided"
            }
            
        result = {
            "completed": False,
            "timeout": False,
            "returncode": None,
            "elapsed_time": 0,
            "error": None,
            "completed_by_log": False
        }
        
        start_time = time.time()
        ahk_log_file = "C:\\LinkHarvesterScript\\cs2_automation.log"
        completion_marker = "All rounds completed!"
        check_interval = 10  # Check log and process status every 10 seconds
        
        try:
            logging.info(f"Waiting for AHK script to complete (timeout: {self.ahk_timeout} seconds)...")
            print(f"Waiting for AHK script to complete (timeout: {self.ahk_timeout/60:.1f} minutes)...")
            print(f"Will also check for completion marker: '{completion_marker}' in log file")
            
            # Start polling loop to check process status and log file
            remaining_time = self.ahk_timeout
            last_log_check_time = 0
            
            while remaining_time > 0:
                # Check if process has exited
                poll_result = process.poll()
                if poll_result is not None:
                    # Process has ended naturally
                    elapsed_time = time.time() - start_time
                    result["completed"] = True
                    result["returncode"] = poll_result
                    result["elapsed_time"] = elapsed_time
                    
                    logging.info(f"AHK script exited after {elapsed_time:.1f} seconds with return code {poll_result}")
                    print(f"AHK script exited after {elapsed_time:.1f} seconds with return code {poll_result}")
                    break
                
                # Check log file for completion marker (only every check_interval seconds)
                current_time = time.time()
                if current_time - last_log_check_time >= check_interval:
                    last_log_check_time = current_time
                    
                    if os.path.exists(ahk_log_file):
                        try:
                            # Read the last few lines of the log file
                            with open(ahk_log_file, 'r') as f:
                                # Use deque to get the last 20 lines efficiently
                                last_lines = deque(f, 20)
                                log_content = ''.join(last_lines)
                                
                                if completion_marker in log_content:
                                    elapsed_time = time.time() - start_time
                                    logging.info(f"Found completion marker in log file after {elapsed_time:.1f} seconds")
                                    print(f"Found completion marker in log file: '{completion_marker}'")
                                    print(f"AHK script logically completed after {elapsed_time:.1f} seconds")
                                    
                                    result["completed"] = True
                                    result["completed_by_log"] = True
                                    result["elapsed_time"] = elapsed_time
                                    
                                    # Terminate the process since it's done but hasn't exited
                                    print("Terminating AHK process that completed but didn't exit...")
                                    process.terminate()
                                    try:
                                        process.wait(timeout=5)
                                        print("AHK process terminated successfully")
                                    except subprocess.TimeoutExpired:
                                        process.kill()
                                        print("AHK process killed forcibly")
                                    
                                    break
                        except Exception as e:
                            logging.error(f"Error reading log file: {e}")
                
                # Wait before next check
                time.sleep(1)
                remaining_time -= 1
                
                # Print status update every 60 seconds
                if remaining_time % 60 == 0:
                    minutes_remaining = remaining_time // 60
                    if minutes_remaining > 0:
                        print(f"Still waiting... {minutes_remaining} minutes remaining before timeout")
            
            # Check if we hit the timeout
            if not result["completed"]:
                elapsed_time = time.time() - start_time
                logging.warning(f"AHK script timed out after {elapsed_time:.1f} seconds")
                print(f"AHK script timed out after {elapsed_time:.1f} seconds")
                
                result["timeout"] = True
                result["elapsed_time"] = elapsed_time
                
                # Attempt to terminate the process
                try:
                    process.terminate()
                    logging.info("Sent termination signal to AHK process")
                    
                    # Give it 5 seconds to terminate gracefully
                    try:
                        process.wait(timeout=5)
                        logging.info("AHK process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        # Force kill if it didn't terminate
                        process.kill()
                        logging.warning("AHK process killed forcibly")
                except Exception as e:
                    logging.error(f"Error terminating AHK process: {str(e)}")
                    result["error"] = f"Error terminating process: {str(e)}"
            
            return result
                
        except Exception as e:
            # Some other error occurred
            elapsed_time = time.time() - start_time
            
            logging.error(f"Error waiting for AHK script: {str(e)}")
            print(f"Error waiting for AHK script: {str(e)}")
            
            result["elapsed_time"] = elapsed_time
            result["error"] = str(e)
            
            # Make sure process is terminated
            try:
                if process.poll() is None:  # If process is still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
            except:
                pass
                
            return result
    
    def run_emergency_disconnect(self):
        """Run the emergency disconnect script to exit CS2 to the main menu"""
        try:
            logging.info("Running emergency disconnect script...")
            print("\nRunning emergency disconnect script to exit CS2 to main menu...")
            
            # Path to the emergency disconnect script
            emergency_script_path = os.path.join(os.getcwd(), "emergency_disconnect.ahk")
            
            # Check if the script exists
            if not os.path.exists(emergency_script_path):
                logging.error(f"Emergency disconnect script not found at: {emergency_script_path}")
                print(f"Error: Emergency disconnect script not found at: {emergency_script_path}")
                return False
            
            # Run the script
            ahk_executable = "C:\\Program Files\\AutoHotkey\\v2\\AutoHotkey.exe"
            
            # Run the script and wait for it to complete (with a short timeout)
            result = subprocess.run(
                [ahk_executable, emergency_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                timeout=15  # 15 second timeout for emergency disconnect
            )
            
            if result.returncode == 0:
                logging.info("Emergency disconnect completed successfully")
                print("Emergency disconnect completed successfully")
                return True
            else:
                logging.error(f"Emergency disconnect failed with return code: {result.returncode}")
                print(f"Emergency disconnect failed with return code: {result.returncode}")
                if result.stderr:
                    logging.error(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("Emergency disconnect script timed out after 15 seconds")
            print("Emergency disconnect script timed out after 15 seconds")
            return False
            
        except Exception as e:
            logging.error(f"Error running emergency disconnect script: {str(e)}")
            print(f"Error running emergency disconnect script: {str(e)}")
            return False
    
    def run_single_server_test(self, server_index=0):
        """Run a test with a single preferred server.
        
        Args:
            server_index: Index of the preferred server to use (defaults to first server)
        """
        if not self.preferred_servers:
            logging.error("No preferred servers defined")
            print("No preferred servers defined")
            return False
        
        if server_index >= len(self.preferred_servers):
            server_index = 0
            
        # Get the selected server
        selected_server = self.preferred_servers[server_index]
        
        logging.info(f"Running single server test with: {selected_server}")
        print(f"Running single server test with: {selected_server}")
        
        # Block all servers first, then unblock just the target
        self.block_all_servers()
        self.unblock_server(selected_server)
                
        # Show what we've done
        print(f"\nServer setup complete. Only {selected_server} should be available.")
        print("Launching AHK script to test connection...")
        
        # Run AHK script (now returns a process object)
        ahk_process = self.run_ahk_script()
        
        # If process was created, monitor it
        success = False
        if ahk_process:
            # Wait for completion or timeout
            result = self.wait_for_ahk_completion(ahk_process)
            
            if result["timeout"]:
                print("\nWARNING: AHK script timed out and was terminated")
                print(f"Script ran for {result['elapsed_time']/60:.1f} minutes before timeout")
                
                # Run emergency disconnect when timeout occurs
                print("\nExecuting emergency disconnect procedure...")
                disconnect_result = self.run_emergency_disconnect()
                
                if disconnect_result:
                    print("Successfully disconnected from match after timeout")
                else:
                    print("WARNING: Failed to execute emergency disconnect after timeout")
                    print("Game may still be in match state")
            
            elif result["completed"]:
                print(f"\nAHK script completed normally in {result['elapsed_time']/60:.1f} minutes")
                if result.get("completed_by_log", False):
                    print("Completion detected via log marker, process was terminated")
                success = True
            else:
                print(f"\nAHK script execution failed: {result.get('error', 'Unknown error')}")
        
        # Unblock all servers at the end
        self.unblock_all_servers()
        print("All servers unblocked.")
        
        return success
    
    def run_all_servers_test(self):
        """Run tests with all preferred servers in sequence using an optimized approach."""
        if not self.preferred_servers:
            logging.error("No preferred servers defined")
            print("No preferred servers defined")
            return False
        
        print(f"\n=== Starting tests for all {len(self.preferred_servers)} preferred servers ===")
        logging.info(f"Starting tests for all {len(self.preferred_servers)} preferred servers")
        
        success_count = 0
        current_active_server = None
        
        # First, block all servers initially
        print("Initially blocking all servers...")
        self.block_all_servers()
        
        for i, server in enumerate(self.preferred_servers):
            print(f"\n--- Testing server {i+1}/{len(self.preferred_servers)}: {server} ---")
            logging.info(f"Testing server {i+1}/{len(self.preferred_servers)}: {server}")
            
            # Efficient server switching: only block the previous and unblock the current
            if current_active_server:
                print(f"Blocking previous server: {current_active_server}")
                self.block_server(current_active_server)
            
            # Unblock the current server
            print(f"Unblocking current server: {server}")
            self.unblock_server(server)
            current_active_server = server
            
            # Show what we've done
            print(f"\nServer setup complete. Only {server} should be available.")
            print("Launching AHK script to test connection...")
            
            # Run AHK script
            ahk_process = self.run_ahk_script()
            
            # If process was created, monitor it
            if ahk_process:
                # Wait for completion or timeout
                result = self.wait_for_ahk_completion(ahk_process)
                
                if result["timeout"]:
                    print("\nWARNING: AHK script timed out and was terminated")
                    print(f"Script ran for {result['elapsed_time']/60:.1f} minutes before timeout")
                    
                    # Run emergency disconnect when timeout occurs
                    print("\nExecuting emergency disconnect procedure...")
                    disconnect_result = self.run_emergency_disconnect()
                    
                    if disconnect_result:
                        print("Successfully disconnected from match after timeout")
                    else:
                        print("WARNING: Failed to execute emergency disconnect after timeout")
                        print("Game may still be in match state")
                
                elif result["completed"]:
                    print(f"\nAHK script completed normally in {result['elapsed_time']/60:.1f} minutes")
                    if result.get("completed_by_log", False):
                        print("Completion detected via log marker, process was terminated")
                    success_count += 1
                else:
                    print(f"\nAHK script execution failed: {result.get('error', 'Unknown error')}")
            
            # If not the last server, give a short pause between tests
            if i < len(self.preferred_servers) - 1:
                pause_time = 1  # second
                print(f"\nPausing for {pause_time} seconds before next server test...")
                time.sleep(pause_time)
        
        # Unblock all servers at the end
        self.unblock_all_servers()
        print("All servers unblocked.")
        
        print(f"\n=== Completed testing {len(self.preferred_servers)} servers ===")
        print(f"Successful tests: {success_count}/{len(self.preferred_servers)}")
        logging.info(f"Completed testing all servers. Success: {success_count}/{len(self.preferred_servers)}")
        
        return True
    
def send_completion_notification(success=True):
    """
    Send a notification that the script has completed running.
    
    Args:
        success: Whether the script completed successfully or with an error
    """
    try:
        # Create API service
        api_service = APIService()
        
        # Send notification based on success status
        message_code = "script-finished-running" if success else "script-error"
        
        # Log the notification attempt
        logging.info(f"Sending completion notification with status: {'success' if success else 'error'}")
        
        # Send the notification
        result, response = api_service.send_notification(message_code)
        
        # Log the result
        if result:
            logging.info("Successfully sent completion notification")
        else:
            logging.warning(f"Failed to send completion notification: {response.get('error', 'Unknown error')}")
    
    except Exception as e:
        # Don't let notification errors affect the script execution
        logging.error(f"Error sending completion notification: {e}")

# Main execution
if __name__ == "__main__":
    try:
        print("=== CS2 Test Server Manager ===")
        print(f"Current time: {datetime.now()}")
        print(f"Log file: {log_file}")
        
        print("Creating test server manager instance...")
        manager = CS2TestServerManager()
        
        # Fetch server data
        print("Fetching server data...")
        if not manager.fetch_server_data():
            logging.error("Failed to fetch server data. Exiting.")
            print("Failed to fetch server data. Exiting.")
            send_completion_notification(success=False)
            sys.exit(1)
        
        # If no preferred servers defined, create an example file
        if not manager.preferred_servers:
            print("No preferred servers found. Creating example file...")
            logging.info("Creating example preferred servers file")
            with open(manager.preferred_servers_file, 'w') as f:
                f.write("# List your preferred servers below, one per line\n")
                f.write("# Use the exact server names as they appear in all_servers.json\n")
                f.write("# Examples:\n")
                f.write("Mumbai (India) (bom2)\n")
                f.write("Singapore (sgp)\n")
            logging.info(f"Example file created: {manager.preferred_servers_file}")
            print(f"Example file created: {manager.preferred_servers_file}")
            print("Please edit this file with your preferred servers and restart the script")
            input("Press Enter to exit...")
            sys.exit(0)
        
        # Offer choice between single server or all servers testing
        if len(manager.preferred_servers) > 1:
            print("\nTest mode options:")
            print("1. Test a single server")
            print("2. Test all preferred servers in sequence")
            
            while True:
                try:
                    mode_choice = int(input("\nEnter test mode (1 or 2): "))
                    if mode_choice in [1, 2]:
                        break
                    else:
                        print("Invalid choice. Please enter 1 or 2.")
                except ValueError:
                    print("Please enter a number.")
            
            if mode_choice == 1:
                # Single server mode - ask which one to test
                print("\nAvailable preferred servers:")
                for i, server in enumerate(manager.preferred_servers):
                    print(f"{i+1}. {server}")
                
                while True:
                    try:
                        choice = int(input("\nEnter server number to test (or 0 to test the first one): "))
                        if choice == 0:
                            server_index = 0
                            break
                        elif 1 <= choice <= len(manager.preferred_servers):
                            server_index = choice - 1
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except ValueError:
                        print("Please enter a number.")
                
                # Run the test with the selected server
                manager.run_single_server_test(server_index)
            else:
                # All servers mode
                manager.run_all_servers_test()
        else:
            # Only one server defined, just run that one
            print(f"\nOnly one preferred server defined: {manager.preferred_servers[0]}")
            manager.run_single_server_test(0)
        
        print("\nTest completed.")
        
        # Send successful completion notification
        send_completion_notification(success=True)
        
    except Exception as e:
        print(f"Unhandled exception: {e}")
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        
        # Send error notification
        send_completion_notification(success=False)
    
    input("Press Enter to exit...")