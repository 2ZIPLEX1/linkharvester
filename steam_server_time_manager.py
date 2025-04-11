import json
import random
import logging
import os
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='server_priority.log',
    filemode='a'
)

def get_utc_now():
    return datetime.now(timezone.utc)

class SteamServerTimeManager:
    """
    Manages Steam server selection based on prioritized time slots,
    with different priorities for each day of the week.
    Selects servers that are in peak hours with randomized ordering within the same timezone.
    """
    
    def __init__(self, timezone_map_file="server_timezone_map.json", 
                 server_history_file="server_history.json",
                 preferred_servers_file="preferred_servers.txt"):
        """
        Initialize the Steam Server Time Manager
        
        Args:
            timezone_map_file: Path to the JSON file mapping servers to timezones
            server_history_file: Path to track server usage history
            preferred_servers_file: File to write the selected servers to
        """
        self.timezone_map_file = timezone_map_file
        self.server_history_file = server_history_file
        self.preferred_servers_file = preferred_servers_file
        self.timezone_map = {}
        self.server_history = {}
        self.last_update_hour = -1
        self.last_update_day = -1
        
        # Priority time slots in local time for each day of the week
        # Day 0 = Monday, 1 = Tuesday, etc.
        self.priority_slots_by_day = {
            # Monday to Thursday (days 0-3)
            0: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "16:00-17:00", "start": 16, "end": 17},
                {"slot": "08:00-09:00", "start": 8, "end": 9}
            ],
            1: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "16:00-17:00", "start": 16, "end": 17},
                {"slot": "08:00-09:00", "start": 8, "end": 9}
            ],
            2: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "16:00-17:00", "start": 16, "end": 17},
                {"slot": "08:00-09:00", "start": 8, "end": 9}
            ],
            3: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "16:00-17:00", "start": 16, "end": 17},
                {"slot": "08:00-09:00", "start": 8, "end": 9}
            ],
            # Friday (day 4)
            4: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "23:00-24:00", "start": 23, "end": 24},
                {"slot": "00:00-01:00", "start": 0, "end": 1},  # Actually early Saturday
                {"slot": "01:00-02:00", "start": 1, "end": 2},  # Actually early Saturday
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "22:00-23:00", "start": 22, "end": 23},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18}
            ],
            # Saturday (day 5)
            5: [
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "23:00-24:00", "start": 23, "end": 24},
                {"slot": "00:00-01:00", "start": 0, "end": 1},  # Actually early Sunday
                {"slot": "01:00-02:00", "start": 1, "end": 2},  # Actually early Sunday
                {"slot": "20:00-21:00", "start": 20, "end": 21},
                {"slot": "21:00-22:00", "start": 21, "end": 22},
                {"slot": "22:00-23:00", "start": 22, "end": 23},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "10:00-11:00", "start": 10, "end": 11},
                {"slot": "11:00-12:00", "start": 11, "end": 12}
            ],
            # Sunday (day 6)
            6: [
                {"slot": "10:00-11:00", "start": 10, "end": 11},
                {"slot": "11:00-12:00", "start": 11, "end": 12},
                {"slot": "19:00-20:00", "start": 19, "end": 20},
                {"slot": "23:00-24:00", "start": 23, "end": 24},
                {"slot": "18:00-19:00", "start": 18, "end": 19},
                {"slot": "17:00-18:00", "start": 17, "end": 18},
                {"slot": "09:00-10:00", "start": 9, "end": 10}
            ]
        }
        
        # Load server timezone mappings
        self.load_timezone_map()
        
        # Load server history
        self.load_server_history()
    
    def load_timezone_map(self):
        """Load the server to timezone mapping"""
        try:
            if os.path.exists(self.timezone_map_file):
                with open(self.timezone_map_file, 'r') as f:
                    self.timezone_map = json.load(f)
                logging.info(f"Loaded timezone map with {len(self.timezone_map)} servers")
            else:
                logging.warning(f"Timezone map file {self.timezone_map_file} not found")
                self.timezone_map = {}
        except Exception as e:
            logging.error(f"Error loading timezone map: {str(e)}")
            self.timezone_map = {}
    
    def load_server_history(self):
        """Load server usage history"""
        try:
            if os.path.exists(self.server_history_file):
                with open(self.server_history_file, 'r') as f:
                    self.server_history = json.load(f)
                logging.info(f"Loaded server history with {len(self.server_history)} entries")
            else:
                logging.info(f"Server history file {self.server_history_file} not found, creating new")
                self.server_history = {}
        except Exception as e:
            logging.error(f"Error loading server history: {str(e)}")
            self.server_history = {}
    
    def save_server_history(self):
        """Save server usage history"""
        try:
            with open(self.server_history_file, 'w') as f:
                json.dump(self.server_history, f, indent=2)
            logging.info(f"Saved server history with {len(self.server_history)} entries")
        except Exception as e:
            logging.error(f"Error saving server history: {str(e)}")
    
    def update_server_usage(self, server_name, profiles_harvested=0):
        """
        Update history when a server has been used
        
        Args:
            server_name: Name of the server that was used
            profiles_harvested: Number of profiles harvested (for statistics)
        """
        now = datetime.now()
        
        if server_name not in self.server_history:
            self.server_history[server_name] = []
        
        # Add the new usage record
        self.server_history[server_name].append({
            "timestamp": now.timestamp(),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "profiles_harvested": profiles_harvested
        })
        
        # Limit the history size (keep only last 10 entries per server)
        if len(self.server_history[server_name]) > 10:
            self.server_history[server_name] = self.server_history[server_name][-10:]
        
        # Save the updated history
        self.save_server_history()
    
    def get_local_hour_for_server(self, server_name, utc_now=None):
        """
        Calculate the current local hour for a given server
        
        Args:
            server_name: Name of the server
            utc_now: Optional pre-calculated UTC time (for batch processing)
            
        Returns:
            tuple: (local_hour, local_datetime) or (None, None) if unknown
        """
        if server_name not in self.timezone_map:
            logging.warning(f"No timezone mapping for server: {server_name}")
            return None, None
        
        # Get the timezone offset
        tz_str = self.timezone_map[server_name]
        
        # Parse the timezone offset
        try:
            if ":" in tz_str:
                # Handle cases like UTC+5:30
                direction = tz_str[3]  # + or -
                hour_part = int(tz_str[4:].split(":")[0])
                minute_part = int(tz_str.split(":")[1])
                
                offset_hours = hour_part + (minute_part / 60)
                if direction == "-":
                    offset_hours = -offset_hours
            else:
                # Handle cases like UTC+8
                offset_hours = int(tz_str[3:])
                if tz_str[3] == "-":
                    offset_hours = -int(tz_str[4:])
            
            # Get current UTC time if not provided
            if utc_now is None:
                utc_now = get_utc_now()
            
            # Calculate local time
            local_time = utc_now + timedelta(hours=offset_hours)
            return local_time.hour, local_time
            
        except Exception as e:
            logging.error(f"Error parsing timezone {tz_str} for server {server_name}: {str(e)}")
            return None, None
    
    def get_priority_for_hour(self, hour, day_of_week):
        """
        Determine the priority of a given local hour based on priority time slots for the day
        
        Args:
            hour: Local hour (0-23)
            day_of_week: Day of the week (0=Monday, 6=Sunday)
            
        Returns:
            int: Priority value (lower = higher priority), or 999 if not in any slot
        """
        # Ensure day_of_week is valid (0-6)
        day_of_week = day_of_week % 7
        
        # Get the priority slots for this day
        priority_slots = self.priority_slots_by_day.get(day_of_week, [])
        
        # Handle empty priority slots (should never happen)
        if not priority_slots:
            return 999
        
        # Handle special cases for hour 0/23 for Friday/Saturday (check next day's early morning slots)
        if hour < 3 and (day_of_week == 5 or day_of_week == 6):  # Saturday or Sunday
            prev_day = day_of_week - 1  # Friday or Saturday
            prev_day_slots = self.priority_slots_by_day.get(prev_day, [])
            
            # Check if there are any slots for hours 0-2 in the previous day's priority list
            for i, slot in enumerate(prev_day_slots):
                if slot["start"] == hour and slot["end"] == hour + 1:
                    # Found an early morning slot, assign its priority
                    return i + 1
        
        # Check regular slots for the current day
        for i, slot in enumerate(priority_slots):
            if slot["start"] <= hour < slot["end"]:
                return i + 1
        
        # Default low priority if not in any defined slot
        return 999
    
    def was_used_recently(self, server_name, minutes=30):
        """
        Check if a server was used in the last N minutes
        
        Args:
            server_name: Name of the server to check
            minutes: Number of minutes to consider as "recent"
            
        Returns:
            bool: True if used recently, False otherwise
        """
        if server_name not in self.server_history:
            return False
        
        if not self.server_history[server_name]:
            return False
        
        # Get the most recent usage
        last_usage = self.server_history[server_name][-1]
        last_timestamp = last_usage["timestamp"]
        
        # Check if it was used in the last N minutes
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        return last_timestamp > cutoff_time
    
    def generate_prioritized_server_list(self):
        """
        Generate a prioritized list of servers based on current time and day of week
        
        Returns:
            list: Prioritized list of server names
        """
        # Get current UTC time
        utc_now = get_utc_now()
        day_of_week = utc_now.weekday()  # 0=Monday, 6=Sunday
        
        # List to hold servers with their priority
        server_priorities = []
        
        # Process each server
        for server_name in self.timezone_map:
            # Skip servers used in the last 30 minutes
            if self.was_used_recently(server_name):
                logging.info(f"Skipping recently used server: {server_name}")
                continue
            
            # Get local hour and datetime at the server location
            local_hour, local_datetime = self.get_local_hour_for_server(server_name, utc_now)
            if local_hour is None:
                continue
            
            # Get the local day of week (may be different from UTC)
            local_day_of_week = local_datetime.weekday()
            
            # Get priority for this hour and day of week
            priority = self.get_priority_for_hour(local_hour, local_day_of_week)
            
            # Store server with priority and a random value for same-priority ordering
            server_priorities.append({
                "server": server_name,
                "priority": priority,
                "local_hour": local_hour,
                "local_day": local_day_of_week,
                "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][local_day_of_week],
                "random": random.random()  # Used for randomizing within priority groups
            })
        
        # Sort by priority (lower first), then by random value
        server_priorities.sort(key=lambda x: (x["priority"], x["random"]))
        
        # Extract just the server names
        prioritized_servers = [s["server"] for s in server_priorities]
        
        # Log the top 10 servers
        if prioritized_servers:
            top_servers = server_priorities[:min(10, len(server_priorities))]
            logging.info(f"Top {len(top_servers)} servers:")
            for s in top_servers:
                logging.info(f"  {s['server']} - Priority: {s['priority']}, Local: {s['day_name']} {s['local_hour']}:00")
        else:
            logging.warning("No servers available after filtering recently used ones")
        
        return prioritized_servers
    
    def write_preferred_servers(self, servers):
        """
        Write the prioritized server list to the preferred servers file
        
        Args:
            servers: List of server names in priority order
        """
        try:
            with open(self.preferred_servers_file, 'w') as f:
                f.write("# Auto-generated preferred servers list based on day/time priority\n")
                f.write("# Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("# Day of week: " + ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][datetime.now().weekday()] + "\n")
                f.write("# Use the exact server names as they appear in all_servers.json\n\n")
                
                for server in servers:
                    f.write(f"{server}\n")
            
            logging.info(f"Wrote {len(servers)} servers to {self.preferred_servers_file}")
            return True
        except Exception as e:
            logging.error(f"Error writing preferred servers file: {str(e)}")
            return False
    
    def update_preferred_servers_list(self):
        """
        Generate a new prioritized server list and write it to the file
        
        Returns:
            bool: Success/failure
        """
        # Get current day and hour for tracking changes
        current_day = get_utc_now().weekday()
        current_hour = get_utc_now().hour
        
        # Generate prioritized server list
        servers = self.generate_prioritized_server_list()
        
        # Write to file
        result = self.write_preferred_servers(servers)
        
        # Update last update time
        if result:
            self.last_update_day = current_day
            self.last_update_hour = current_hour
        
        return result
    
    def check_and_update_preferred_servers(self):
        """
        Check if it's time to update the preferred servers list and do so if needed
        
        Returns:
            bool: True if updated, False otherwise
        """
        current_day = get_utc_now().weekday()
        current_hour = get_utc_now().hour
        
        # Update if this is the first run, the day has changed, or the hour has changed
        if (self.last_update_hour == -1 or 
            self.last_update_day != current_day or 
            current_hour != self.last_update_hour):
            
            logging.info(f"Time changed from day {self.last_update_day}, hour {self.last_update_hour} to day {current_day}, hour {current_hour}, updating server list")
            return self.update_preferred_servers_list()
        
        return False
    
    def log_server_performance(self, server_name, start_time, end_time, profiles_harvested):
        """
        Log server performance data
        
        Args:
            server_name: Name of the server
            start_time: Start time of the session (datetime)
            end_time: End time of the session (datetime)
            profiles_harvested: Number of profiles harvested
        """
        # Calculate session duration in minutes
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # Calculate harvest rate
        harvest_rate = profiles_harvested / duration_minutes if duration_minutes > 0 else 0
        
        # Get local time at the server location
        local_hour, local_datetime = self.get_local_hour_for_server(server_name)
        
        # Get day of week at server location
        local_day_name = "Unknown"
        if local_datetime:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            local_day_name = day_names[local_datetime.weekday()]
        
        local_time_str = f"Unknown"
        if local_hour is not None:
            local_time_str = f"{local_hour}:00-{local_hour+1}:00 ({local_day_name})"
        
        # Format for log
        log_entry = {
            "server": server_name,
            "utc_start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "utc_end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "local_time": local_time_str,
            "duration_minutes": round(duration_minutes, 1),
            "profiles_harvested": profiles_harvested,
            "harvest_rate": round(harvest_rate, 2)
        }
        
        # Log to file and update server history
        logging.info(f"Server performance: {json.dumps(log_entry)}")
        self.update_server_usage(server_name, profiles_harvested)
        
        return log_entry


# Example usage:
if __name__ == "__main__":
    # Create an example timezone map file if it doesn't exist
    if not os.path.exists("server_timezone_map.json"):
        example_map = {
            "London (England) (lhr)": "UTC+1",
            "Paris (France) (par)": "UTC+2",
            "Hong Kong (hkg)": "UTC+8",
            "New York (USA) (nyc)": "UTC-4"
        }
        with open("server_timezone_map.json", "w") as f:
            json.dump(example_map, f, indent=2)
        print("Created example server_timezone_map.json")
    
    # Create the manager
    manager = SteamServerTimeManager()
    
    # Update the server list
    manager.update_preferred_servers_list()
    
    # Simulate some server usage
    manager.log_server_performance(
        "Hong Kong (hkg)",
        datetime.now() - timedelta(hours=1),
        datetime.now() - timedelta(minutes=30),
        24
    )
    
    print("Generated preferred_servers.txt with prioritized servers based on current day and time")