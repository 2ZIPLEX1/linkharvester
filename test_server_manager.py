import requests
import json
import subprocess
import os
import sys
import logging
from datetime import datetime

# Setup logging to OneDrive Documents folder
home_dir = os.path.expanduser("~")
log_directory = "C:\\LinkHarvesterScript"
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
    
    def unblock_all_servers(self):
        """Unblock all servers"""
        logging.info("Unblocking all servers")
        print("Unblocking all servers")
        
        for server_name in self.servers_data:
            self.unblock_server(server_name)
        
        return True
    
    def run_ahk_script(self):
        """Run the AutoHotkey script"""
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
            
            # Ask for confirmation before proceeding
            confirm = input("\nReady to proceed? (y/n): ").lower()
            if confirm != 'y' and confirm != 'yes':
                logging.info("User canceled AHK script execution")
                print("AHK script execution canceled.")
                return False
            
            ahk_executable = "C:\\Program Files\\AutoHotkey\\v2\\AutoHotkey.exe"
            print("\nLaunching AHK script...")
            result = subprocess.run([ahk_executable, self.ahk_script_path], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                logging.error(f"AHK script failed: {result.stderr}")
                print(f"AHK script failed: {result.stderr}")
                return False
            
            logging.info("AHK script completed successfully")
            print("AHK script completed successfully")
            return True
        except Exception as e:
            logging.error(f"Error running AHK script: {str(e)}")
            print(f"Error running AHK script: {str(e)}")
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
        
        # Make sure all servers are unblocked first
        self.unblock_all_servers()
        
        # Block all other servers except the selected one
        for server_name in self.servers_data:
            if server_name != selected_server:
                self.block_server(server_name)
                
        # Show what we've done
        print(f"\nServer setup complete. Only {selected_server} should be available.")
        print("Launching AHK script to test connection...")
        
        # Run AHK script
        self.run_ahk_script()
        
        return True

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
            sys.exit(1)
        
        # If no preferred servers defined, create an example file
        if not manager.preferred_servers:
            print("No preferred servers found. Creating example file...")
            logging.info("Creating example preferred servers file")
            with open(manager.preferred_servers_file, 'w') as f:
                f.write("# List your preferred servers below, one per line\n")
                f.write("# Use the exact server names as they appear in all_servers.json\n")
                f.write("# Examples:\n")
                f.write("Stockholm (Sweden) (sto)\n")
                f.write("Vienna (Austria) (vie)\n")
                f.write("Warsaw (Poland) (waw)\n")
            logging.info(f"Example file created: {manager.preferred_servers_file}")
            print(f"Example file created: {manager.preferred_servers_file}")
            print("Please edit this file with your preferred servers and restart the script")
            input("Press Enter to exit...")
            sys.exit(0)
        
        # If we have multiple servers, ask which one to test
        if len(manager.preferred_servers) > 1:
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
        else:
            server_index = 0
        
        # Run the test with the selected server
        manager.run_single_server_test(server_index)
        
        # Ask if we should unblock all servers before exiting
        choice = input("\nDo you want to unblock all servers before exiting? (y/n): ").lower()
        if choice == 'y' or choice == 'yes':
            manager.unblock_all_servers()
            print("All servers unblocked.")
        else:
            print("Servers will remain in their current blocked/unblocked state.")
            
        print("\nTest completed.")
        
    except Exception as e:
        print(f"Unhandled exception: {e}")
        logging.error(f"Unhandled exception: {e}", exc_info=True)
    
    input("Press Enter to exit...")