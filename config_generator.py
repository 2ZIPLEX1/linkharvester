import os
import json

# Default configuration
config = {
    "cs2_executable": "D:\\SteamLibrary\\steamapps\\common\\Counter-Strike Global Offensive\\game\\bin\\win64\\cs2.exe",
    "steam_executable": "C:\\Program Files (x86)\\Steam\\steam.exe",
    "server_cycle_delay": 5,  # seconds between server cycles
    "match_timeout": 180,  # seconds to wait for a match
    "match_start_wait": 30,  # seconds to wait for match to start
    "play_button_x": 960,
    "play_button_y": 540,
    "mode_selection_x": 960,
    "mode_selection_y": 600,
    "find_match_x": 960,
    "find_match_y": 700,
    "accept_match_x": 960,
    "accept_match_y": 580
}

# Path for configuration files
home_dir = os.path.expanduser("~")
config_dir = os.path.join(home_dir, "OneDrive", "Документы", "AutoHotkey", "data")
os.makedirs(config_dir, exist_ok=True)

# JSON config file (for Python)
json_config_file = os.path.join(config_dir, "config.json")

# Text config file (for AHK)
text_config_file = os.path.join(config_dir, "config.txt")

# Check if JSON config file already exists
if os.path.exists(json_config_file):
    try:
        with open(json_config_file, 'r') as f:
            existing_config = json.load(f)
            # Update default config with existing values
            config.update(existing_config)
            print(f"Updated configuration with existing values from {json_config_file}")
    except Exception as e:
        print(f"Error reading existing config: {e}")

# Save JSON configuration for Python
try:
    with open(json_config_file, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"JSON configuration saved to {json_config_file}")
except Exception as e:
    print(f"Error saving JSON configuration: {e}")

# Save text configuration for AHK
try:
    with open(text_config_file, 'w') as f:
        for key, value in config.items():
            # Skip nested dictionaries, only write simple key=value pairs
            if not isinstance(value, dict):
                f.write(f"{key}={value}\n")
    print(f"Text configuration saved to {text_config_file}")
except Exception as e:
    print(f"Error saving text configuration: {e}")

print("\nCurrent configuration:")
for key, value in config.items():
    if not isinstance(value, dict):
        print(f"{key}: {value}")
    else:
        print(f"{key}: {value}")

print("\nYou can edit these configuration files directly to customize settings.")