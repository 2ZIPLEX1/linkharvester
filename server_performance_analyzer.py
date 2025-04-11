import json
import os
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='performance_analyzer.log',
    filemode='a'
)

class ServerPerformanceAnalyzer:
    """
    Analyzes server performance data to generate insights
    on harvest rates by time slot and region
    """
    
    def __init__(self, 
                 server_history_file="server_history.json",
                 timezone_map_file="server_timezone_map.json",
                 output_dir="reports"):
        """
        Initialize the Server Performance Analyzer
        
        Args:
            server_history_file: Path to server history JSON file
            timezone_map_file: Path to server timezone mapping
            output_dir: Directory to save reports and charts
        """
        self.server_history_file = server_history_file
        self.timezone_map_file = timezone_map_file
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load data
        self.server_history = self.load_server_history()
        self.timezone_map = self.load_timezone_map()
    
    def load_server_history(self):
        """Load server usage history"""
        try:
            if os.path.exists(self.server_history_file):
                with open(self.server_history_file, 'r') as f:
                    history = json.load(f)
                logging.info(f"Loaded server history with {len(history)} servers")
                return history
            else:
                logging.warning(f"Server history file not found: {self.server_history_file}")
                return {}
        except Exception as e:
            logging.error(f"Error loading server history: {str(e)}")
            return {}
    
    def load_timezone_map(self):
        """Load server to timezone mapping"""
        try:
            if os.path.exists(self.timezone_map_file):
                with open(self.timezone_map_file, 'r') as f:
                    timezone_map = json.load(f)
                logging.info(f"Loaded timezone map with {len(timezone_map)} servers")
                return timezone_map
            else:
                logging.warning(f"Timezone map file not found: {self.timezone_map_file}")
                return {}
        except Exception as e:
            logging.error(f"Error loading timezone map: {str(e)}")
            return {}
    
    def get_server_timezone_offset(self, server_name):
        """
        Get the UTC offset for a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            float: UTC offset in hours, or None if unknown
        """
        if server_name not in self.timezone_map:
            return None
        
        tz_str = self.timezone_map[server_name]
        
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
            
            return offset_hours
        except Exception as e:
            logging.error(f"Error parsing timezone {tz_str} for server {server_name}: {str(e)}")
            return None
    
    def get_local_time_from_utc(self, utc_time_str, server_name):
        """
        Convert UTC time to local time at server location
        
        Args:
            utc_time_str: UTC time as string (YYYY-MM-DD HH:MM:SS)
            server_name: Name of the server
            
        Returns:
            datetime: Local time at server location, or None if conversion failed
        """
        try:
            # Parse UTC time
            utc_time = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S")
            
            # Get timezone offset
            offset = self.get_server_timezone_offset(server_name)
            if offset is None:
                return None
            
            # Convert to local time
            local_time = utc_time + timedelta(hours=offset)
            return local_time
        except Exception as e:
            logging.error(f"Error converting UTC time to local time: {str(e)}")
            return None
    
    def analyze_performance_by_hour(self, days_ago=7):
        """
        Analyze server performance grouped by local hour
        
        Args:
            days_ago: Number of days to look back
            
        Returns:
            dict: Performance data by hour
        """
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(days=days_ago)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Data structure to hold results
        hourly_performance = defaultdict(lambda: {
            "sessions": 0,
            "total_profiles": 0,
            "total_minutes": 0,
            "servers": set()
        })
        
        # Process each server's history
        for server_name, records in self.server_history.items():
            # Skip unknown timezones
            if server_name not in self.timezone_map:
                continue
            
            for record in records:
                # Skip old records
                if record["timestamp"] < cutoff_timestamp:
                    continue
                
                # Get local time at server location
                local_time = self.get_local_time_from_utc(record["datetime"], server_name)
                if local_time is None:
                    continue
                
                # Get local hour
                local_hour = local_time.hour
                
                # Get metrics from record
                profiles = record.get("profiles_harvested", 0)
                
                # If duration not available, estimate it (use 20 minutes as default)
                duration = record.get("duration_minutes", 20)
                
                # Update hourly stats
                hourly_performance[local_hour]["sessions"] += 1
                hourly_performance[local_hour]["total_profiles"] += profiles
                hourly_performance[local_hour]["total_minutes"] += duration
                hourly_performance[local_hour]["servers"].add(server_name)
        
        # Calculate averages and format results
        result = {}
        for hour, data in hourly_performance.items():
            # Calculate average harvest rate (profiles per hour)
            hours_spent = data["total_minutes"] / 60
            harvest_rate = data["total_profiles"] / hours_spent if hours_spent > 0 else 0
            
            result[hour] = {
                "sessions": data["sessions"],
                "total_profiles": data["total_profiles"],
                "total_hours": round(hours_spent, 2),
                "avg_harvest_rate": round(harvest_rate, 2),
                "server_count": len(data["servers"]),
                "servers": list(data["servers"])
            }
        
        return result
    
    def analyze_performance_by_timezone(self, days_ago=7):
        """
        Analyze server performance grouped by timezone
        
        Args:
            days_ago: Number of days to look back
            
        Returns:
            dict: Performance data by timezone
        """
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(days=days_ago)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Group servers by timezone
        timezone_servers = defaultdict(list)
        for server, tz in self.timezone_map.items():
            timezone_servers[tz].append(server)
        
        # Data structure to hold results
        timezone_performance = defaultdict(lambda: {
            "sessions": 0,
            "total_profiles": 0,
            "total_minutes": 0,
            "servers": set()
        })
        
        # Process each server's history
        for server_name, records in self.server_history.items():
            # Skip unknown timezones
            if server_name not in self.timezone_map:
                continue
            
            # Get server timezone
            timezone = self.timezone_map[server_name]
            
            for record in records:
                # Skip old records
                if record["timestamp"] < cutoff_timestamp:
                    continue
                
                # Get metrics from record
                profiles = record.get("profiles_harvested", 0)
                
                # If duration not available, estimate it (use 20 minutes as default)
                duration = record.get("duration_minutes", 20)
                
                # Update timezone stats
                timezone_performance[timezone]["sessions"] += 1
                timezone_performance[timezone]["total_profiles"] += profiles
                timezone_performance[timezone]["total_minutes"] += duration
                timezone_performance[timezone]["servers"].add(server_name)
        
        # Calculate averages and format results
        result = {}
        for timezone, data in timezone_performance.items():
            # Calculate average harvest rate (profiles per hour)
            hours_spent = data["total_minutes"] / 60
            harvest_rate = data["total_profiles"] / hours_spent if hours_spent > 0 else 0
            
            result[timezone] = {
                "sessions": data["sessions"],
                "total_profiles": data["total_profiles"],
                "total_hours": round(hours_spent, 2),
                "avg_harvest_rate": round(harvest_rate, 2),
                "server_count": len(data["servers"]),
                "servers": list(data["servers"])
            }
        
        return result
    
    def analyze_top_servers(self, days_ago=7, top_n=10):
        """
        Analyze performance of top servers
        
        Args:
            days_ago: Number of days to look back
            top_n: Number of top servers to return
            
        Returns:
            list: Top performing servers
        """
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(days=days_ago)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Data structure to hold server performance
        server_performance = {}
        
        # Process each server's history
        for server_name, records in self.server_history.items():
            # Initialize server stats
            server_performance[server_name] = {
                "total_profiles": 0,
                "total_minutes": 0,
                "sessions": 0
            }
            
            # Count recent records
            recent_records = 0
            
            for record in records:
                # Skip old records
                if record["timestamp"] < cutoff_timestamp:
                    continue
                
                recent_records += 1
                
                # Get metrics from record
                profiles = record.get("profiles_harvested", 0)
                
                # If duration not available, estimate it (use 20 minutes as default)
                duration = record.get("duration_minutes", 20)
                
                # Update server stats
                server_performance[server_name]["total_profiles"] += profiles
                server_performance[server_name]["total_minutes"] += duration
                server_performance[server_name]["sessions"] += 1
            
            # Skip servers with no recent activity
            if recent_records == 0:
                del server_performance[server_name]
        
        # Calculate harvest rate for each server
        for server, stats in server_performance.items():
            hours_spent = stats["total_minutes"] / 60
            stats["harvest_rate"] = stats["total_profiles"] / hours_spent if hours_spent > 0 else 0
            stats["total_hours"] = hours_spent
            
            # Add timezone info if available
            if server in self.timezone_map:
                stats["timezone"] = self.timezone_map[server]
            else:
                stats["timezone"] = "Unknown"
        
        # Sort servers by harvest rate
        sorted_servers = sorted(
            server_performance.items(),
            key=lambda x: x[1]["harvest_rate"],
            reverse=True
        )
        
        # Return top N servers
        return sorted_servers[:top_n]
    
    def generate_hourly_performance_chart(self, days_ago=7):
        """
        Generate a chart showing harvest performance by hour
        
        Args:
            days_ago: Number of days to look back
            
        Returns:
            str: Path to saved chart
        """
        try:
            # Get hourly performance data
            hourly_data = self.analyze_performance_by_hour(days_ago)
            
            # Prepare chart data
            hours = sorted(hourly_data.keys())
            harvest_rates = [hourly_data[hour]["avg_harvest_rate"] for hour in hours]
            total_profiles = [hourly_data[hour]["total_profiles"] for hour in hours]
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Plot harvest rates by hour
            ax1.bar(hours, harvest_rates, color='blue', alpha=0.7)
            ax1.set_xlabel('Local Hour (24h format)')
            ax1.set_ylabel('Profiles per Hour')
            ax1.set_title(f'Average Harvest Rate by Local Hour (Last {days_ago} Days)')
            ax1.set_xticks(hours)
            ax1.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(harvest_rates):
                if v > 0:
                    ax1.text(hours[i], v + 0.5, f"{v:.1f}", ha='center')
            
            # Plot total profiles by hour
            ax2.bar(hours, total_profiles, color='green', alpha=0.7)
            ax2.set_xlabel('Local Hour (24h format)')
            ax2.set_ylabel('Total Profiles Harvested')
            ax2.set_title(f'Total Profiles Harvested by Local Hour (Last {days_ago} Days)')
            ax2.set_xticks(hours)
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(total_profiles):
                if v > 0:
                    ax2.text(hours[i], v + 0.5, str(v), ha='center')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(self.output_dir, f"hourly_performance_{days_ago}days.png")
            plt.savefig(chart_path)
            plt.close()
            
            logging.info(f"Generated hourly performance chart: {chart_path}")
            return chart_path
            
        except Exception as e:
            logging.error(f"Error generating hourly performance chart: {str(e)}")
            return None
    
    def generate_timezone_performance_chart(self, days_ago=7):
        """
        Generate a chart showing harvest performance by timezone
        
        Args:
            days_ago: Number of days to look back
            
        Returns:
            str: Path to saved chart
        """
        try:
            # Get timezone performance data
            timezone_data = self.analyze_performance_by_timezone(days_ago)
            
            # Prepare chart data
            timezones = sorted(timezone_data.keys())
            harvest_rates = [timezone_data[tz]["avg_harvest_rate"] for tz in timezones]
            total_profiles = [timezone_data[tz]["total_profiles"] for tz in timezones]
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            
            # Plot harvest rates by timezone
            bars1 = ax1.bar(timezones, harvest_rates, color='blue', alpha=0.7)
            ax1.set_xlabel('Timezone')
            ax1.set_ylabel('Profiles per Hour')
            ax1.set_title(f'Average Harvest Rate by Timezone (Last {days_ago} Days)')
            ax1.set_xticklabels(timezones, rotation=45, ha='right')
            ax1.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(harvest_rates):
                if v > 0:
                    ax1.text(i, v + 0.5, f"{v:.1f}", ha='center')
            
            # Plot total profiles by timezone
            bars2 = ax2.bar(timezones, total_profiles, color='green', alpha=0.7)
            ax2.set_xlabel('Timezone')
            ax2.set_ylabel('Total Profiles Harvested')
            ax2.set_title(f'Total Profiles Harvested by Timezone (Last {days_ago} Days)')
            ax2.set_xticklabels(timezones, rotation=45, ha='right')
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(total_profiles):
                if v > 0:
                    ax2.text(i, v + 0.5, str(v), ha='center')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(self.output_dir, f"timezone_performance_{days_ago}days.png")
            plt.savefig(chart_path)
            plt.close()
            
            logging.info(f"Generated timezone performance chart: {chart_path}")
            return chart_path
            
        except Exception as e:
            logging.error(f"Error generating timezone performance chart: {str(e)}")
            return None
    
    def generate_top_servers_chart(self, days_ago=7, top_n=10):
        """
        Generate a chart showing top performing servers
        
        Args:
            days_ago: Number of days to look back
            top_n: Number of top servers to display
            
        Returns:
            str: Path to saved chart
        """
        try:
            # Get top servers data
            top_servers = self.analyze_top_servers(days_ago, top_n)
            
            # Prepare chart data
            servers = [s[0] for s in top_servers]
            harvest_rates = [s[1]["harvest_rate"] for s in top_servers]
            total_profiles = [s[1]["total_profiles"] for s in top_servers]
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Plot harvest rates
            y_pos = range(len(servers))
            ax1.barh(y_pos, harvest_rates, color='blue', alpha=0.7)
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels(servers)
            ax1.set_xlabel('Profiles per Hour')
            ax1.set_title(f'Top {len(top_servers)} Servers by Harvest Rate (Last {days_ago} Days)')
            ax1.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(harvest_rates):
                if v > 0:
                    ax1.text(v + 0.5, i, f"{v:.1f}", va='center')
            
            # Plot total profiles
            ax2.barh(y_pos, total_profiles, color='green', alpha=0.7)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(servers)
            ax2.set_xlabel('Total Profiles Harvested')
            ax2.set_title(f'Top {len(top_servers)} Servers by Total Profiles (Last {days_ago} Days)')
            ax2.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(total_profiles):
                if v > 0:
                    ax2.text(v + 0.5, i, str(v), va='center')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(self.output_dir, f"top_servers_{days_ago}days.png")
            plt.savefig(chart_path)
            plt.close()
            
            logging.info(f"Generated top servers chart: {chart_path}")
            return chart_path
            
        except Exception as e:
            logging.error(f"Error generating top servers chart: {str(e)}")
            return None
    
    def generate_performance_report(self, days_ago=7, top_n=10):
        """
        Generate a comprehensive performance report
        
        Args:
            days_ago: Number of days to look back
            top_n: Number of top servers to include
            
        Returns:
            str: Path to saved report
        """
        try:
            # Get performance data
            hourly_data = self.analyze_performance_by_hour(days_ago)
            timezone_data = self.analyze_performance_by_timezone(days_ago)
            top_servers = self.analyze_top_servers(days_ago, top_n)
            
            # Generate charts
            self.generate_hourly_performance_chart(days_ago)
            self.generate_timezone_performance_chart(days_ago)
            self.generate_top_servers_chart(days_ago, top_n)
            
            # Create report content
            report = f"# Steam Server Performance Report\n\n"
            report += f"## Report Period: Last {days_ago} Days\n"
            report += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Top servers section
            report += f"## Top {len(top_servers)} Performing Servers\n\n"
            report += "| Server | Timezone | Total Profiles | Hours | Harvest Rate |\n"
            report += "|--------|----------|----------------|-------|-------------|\n"
            
            for server, stats in top_servers:
                report += f"| {server} | {stats['timezone']} | {stats['total_profiles']} | {stats['total_hours']:.1f} | {stats['harvest_rate']:.1f} |\n"
            
            report += "\n"
            
            # Best hours section
            report += "## Performance by Local Hour\n\n"
            report += "| Hour | Sessions | Total Profiles | Hours | Harvest Rate |\n"
            report += "|------|----------|----------------|-------|-------------|\n"
            
            for hour in sorted(hourly_data.keys()):
                data = hourly_data[hour]
                report += f"| {hour:02d}:00 | {data['sessions']} | {data['total_profiles']} | {data['total_hours']:.1f} | {data['avg_harvest_rate']:.1f} |\n"
            
            report += "\n"
            
            # Timezone section
            report += "## Performance by Timezone\n\n"
            report += "| Timezone | Servers | Sessions | Total Profiles | Hours | Harvest Rate |\n"
            report += "|----------|---------|----------|----------------|-------|-------------|\n"
            
            for timezone in sorted(timezone_data.keys()):
                data = timezone_data[timezone]
                report += f"| {timezone} | {data['server_count']} | {data['sessions']} | {data['total_profiles']} | {data['total_hours']:.1f} | {data['avg_harvest_rate']:.1f} |\n"
            
            # Save report
            report_path = os.path.join(self.output_dir, f"performance_report_{days_ago}days.md")
            with open(report_path, 'w') as f:
                f.write(report)
            
            logging.info(f"Generated performance report: {report_path}")
            return report_path
            
        except Exception as e:
            logging.error(f"Error generating performance report: {str(e)}")
            return None


if __name__ == "__main__":
    # Create an example history file if it doesn't exist
    if not os.path.exists("server_history.json"):
        example_history = {
            "London (England) (lhr)": [
                {
                    "timestamp": datetime.now().timestamp() - 86400,
                    "datetime": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "profiles_harvested": 15,
                    "duration_minutes": 25
                },
                {
                    "timestamp": datetime.now().timestamp() - 43200,
                    "datetime": (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                    "profiles_harvested": 18,
                    "duration_minutes": 30
                }
            ],
            "Hong Kong (hkg)": [
                {
                    "timestamp": datetime.now().timestamp() - 172800,
                    "datetime": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    "profiles_harvested": 24,
                    "duration_minutes": 35
                }
            ]
        }
        
        with open("server_history.json", "w") as f:
            json.dump(example_history, f, indent=2)
        print("Created example server_history.json")
    
    # Create the analyzer
    analyzer = ServerPerformanceAnalyzer()
    
    # Generate reports
    report_path = analyzer.generate_performance_report(days_ago=7)
    print(f"Generated performance report: {report_path}")
    
    # Generate charts
    hourly_chart = analyzer.generate_hourly_performance_chart()
    timezone_chart = analyzer.generate_timezone_performance_chart()
    servers_chart = analyzer.generate_top_servers_chart()
    
    print("Generated performance charts in the reports directory")