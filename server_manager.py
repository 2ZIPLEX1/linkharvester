import requests
import json
import subprocess
import os
import sys
import time
import logging
from datetime import datetime

# Print startup message to console (will be visible in PowerShell window)
print("CS2 Server Manager starting...")
print(f"Script path: {os.path.abspath(__file__)}")
print(f"Current directory: {os.getcwd()}")

# Setup logging to OneDrive Documents folder
home_dir = os.path.expanduser("~")
log_directory = os.path.join(home_dir, "OneDrive", "Документы", "AutoHotkey")

# Create directories if they don't exist
try:
    os.makedirs(log_directory, exist_ok=True)
    print(f"Log directory: {log_directory}")
    
    # Create data directory
    data_directory = os.path.join(log_directory, "data")
    os.makedirs(data_directory, exist_ok=True)
    print(f"Data directory: {data_directory}")
except Exception as e:
    print(f"Error creating directories: {e}")
    # Fallback to script directory
    log_directory = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(log_directory, "data")
    os.makedirs(data_directory, exist_ok=True)
    print(f"Using fallback directories: {log_directory}, {data_directory}")

# Configure logging
log_file = os.path.join(log_directory, "cs2_server_manager.log")
print(f"Log file: {log_file}")

try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='a'  # Append mode
    )
    logging.info("=== CS2 Server Manager Started ===")
except Exception as e:
    print(f"Error setting up logging: {e}")
    sys.exit(1)

class CS2ServerManager:
    def __init__(self):
        self.api_url = "https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/?appid=730"
        self.servers_data = {}
        self.preferred_servers = []
        self.current_server_index = 0
        self.netsh_path = os.path.join(os.environ["SystemRoot"], "System32", "netsh.exe")
        self.ahk_script_path = os.path.join(os.getcwd(), "cs2_automation.ahk")
        
        # Set up data directories
        self.data_directory = data_directory
        self.preferred_servers_file = os.path.join(self.data_directory, "preferred_servers.txt")
        self.all_servers_file = os.path.join(self.data_directory, "all_servers.json")
        
        logging.info(f"Preferred servers file: {self.preferred_servers_file}")
        logging.info(f"All servers file: {self.all_servers_file}")
        
        # Load configuration
        self.load_config()
        
        # Load preferred servers if file exists
        self.load_preferred_servers()
        
    def load_preferred_servers(self):
        """Load preferred servers from file"""
        try:
            if os.path.exists(self.preferred_servers_file):
                with open(self.preferred_servers_file, 'r') as f:
                    self.preferred_servers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logging.info(f"Loaded {len(self.preferred_servers)} preferred servers")
            else:
                logging.warning(f"Preferred servers file not found: {self.preferred_servers_file}")
        except Exception as e:
            logging.error(f"Error loading preferred servers: {str(e)}")
    
    def fetch_server_data(self):
        """Fetch server data from Steam API"""
        try:
            logging.info("Fetching server data from Steam API...")
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
            
            # Save full server list for reference
            with open(self.all_servers_file, "w") as f:
                json.dump(self.servers_data, f, indent=4)
            
            return True
        except Exception as e:
            logging.error(f"Error fetching server data: {str(e)}")
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
            return False
        
        server_rule_name = f"CS2ServerPicker_{server_name.replace(' ', '')}"
        cmd = [
            self.netsh_path, "advfirewall", "firewall", "add", "rule",
            f"name={server_rule_name}", "dir=out", "action=block", "protocol=ANY",
            f"remoteip={self.servers_data[server_name]}"
        ]
        
        try:
            logging.info(f"Blocking server: {server_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logging.error(f"Failed to block server: {result.stderr}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error blocking server: {str(e)}")
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
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logging.error(f"Failed to unblock server: {result.stderr}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error unblocking server: {str(e)}")
            return False
    
    def block_all_except(self, exception_server_name):
        """Block all servers except the specified one"""
        logging.info(f"Blocking all servers except: {exception_server_name}")
        
        # First, unblock the exception server if needed
        if exception_server_name in self.servers_data:
            self.unblock_server(exception_server_name)
        
        # Block all other servers
        for server_name in self.servers_data:
            if server_name != exception_server_name:
                self.block_server(server_name)
        
        return True
    
    def unblock_all_servers(self):
        """Unblock all servers"""
        logging.info("Unblocking all servers")
        
        for server_name in self.servers_data:
            self.unblock_server(server_name)
        
        return True
    
    def load_config(self):
        """Load configuration from file"""
        config_file = os.path.join(self.data_directory, "config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                    logging.info(f"Configuration loaded from {config_file}")
                    return True
            else:
                logging.warning(f"Configuration file not found: {config_file}")
                self.config = {}
                return False
        except Exception as e:
            logging.error(f"Error loading configuration: {str(e)}")
            self.config = {}
            return False
            
    def run_ahk_script(self):
        """Run the AutoHotkey script"""
        try:
            logging.info("Running AHK script")
            ahk_executable = "C:\\Program Files\\AutoHotkey\\v2\\AutoHotkey.exe"
            result = subprocess.run([ahk_executable, self.ahk_script_path], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                logging.error(f"AHK script failed: {result.stderr}")
                return False
            
            logging.info("AHK script completed successfully")
            return True
        except Exception as e:
            logging.error(f"Error running AHK script: {str(e)}")
            return False
    
    def cycle_to_next_server(self):
        """Switch to the next server in the preferred list"""
        if not self.preferred_servers:
            logging.error("No preferred servers defined")
            return False
        
        # Get current and next server
        current_server = self.preferred_servers[self.current_server_index]
        self.current_server_index = (self.current_server_index + 1) % len(self.preferred_servers)
        next_server = self.preferred_servers[self.current_server_index]
        
        logging.info(f"Cycling from {current_server} to {next_server}")
        
        # Block current server and unblock next server
        self.block_server(current_server)
        self.unblock_server(next_server)
        
        return next_server
    
    def run_server_cycle(self):
        """Run a complete cycle through all preferred servers"""
        if not self.preferred_servers:
            logging.error("No preferred servers defined")
            return False
        
        logging.info("Starting server cycle")
        total_servers = len(self.preferred_servers)
        
        for i in range(total_servers):
            current_server = self.preferred_servers[self.current_server_index]
            logging.info(f"Processing server {i+1}/{total_servers}: {current_server}")
            
            # Block all servers except current one
            self.block_all_except(current_server)
            
            # Run AHK script
            self.run_ahk_script()
            
            # Move to next server
            self.cycle_to_next_server()
            
            # Wait briefly before next iteration
            time.sleep(5)
        
        logging.info("Server cycle completed")
        return True

# Main execution
if __name__ == "__main__":
    try:
        print("=== CS2 Server Manager Starting ===")
        print(f"Current time: {datetime.now()}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Log directory: {log_directory}")
        print(f"Log file: {log_file}")
        
        print("Creating server manager instance...")
        manager = CS2ServerManager()
        
        # Fetch server data
        print("Fetching server data...")
        if not manager.fetch_server_data():
            logging.error("Failed to fetch server data. Exiting.")
            print("Failed to fetch server data. See log for details.")
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
        
        # Start the continuous cycle
        print("Starting continuous server cycle...")
        try:
            while True:
                manager.run_server_cycle()
                logging.info("Completed full cycle, starting again...")
                print("Completed full cycle, starting again...")
                time.sleep(10)
        except KeyboardInterrupt:
            print("Script stopped by user")
            logging.info("Script stopped by user")
            # Unblock all servers before exiting
            manager.unblock_all_servers()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        try:
            logging.error(f"Unhandled exception: {e}", exc_info=True)
        except:
            pass
    
    input("Press Enter to exit...")