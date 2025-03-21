import os
import json

# Default configuration
config = {
    "cs2_executable": "D:\\SteamLibrary\\steamapps\\common\\Counter-Strike Global Offensive\\game\\bin\\win64\\cs2.exe",
    "steam_executable": "C:\\Program Files (x86)\\Steam\\steam.exe",
    "server_cycle_delay": 5,  # seconds between server cycles
    "match_timeout": 180,  # seconds to wait for a match
    "wait_between_clicks": 1500,  # milliseconds to wait between UI interactions
    "max_wait_for_match": 120,  # seconds to wait for match to start
    "color_tolerance": 20,  # tolerance for color matching
    
    # Updated UI coordinates for the CS2 interface
    "play_button_x": 985,
    "play_button_y": 30,
    "mode_selection_x": 813,
    "mode_selection_y": 85,
    "league_selection_x": 906,
    "league_selection_y": 130,
    "accept_match_x": 1690,
    "accept_match_y": 1030,
    
    # Success scenario - Spectator button
    "spectator_button_x": 1592,
    "spectator_button_y": 1031,
    "spectator_button_color": "E9E8E4",  # without 0x prefix for compatibility

    # Updated spectator button configuration
    "spectator_button_left_x": 1577,  # Upper-left X
    "spectator_button_left_y": 1008,  # Upper-left Y
    "spectator_button_right_x": 1699, # Lower-right X
    "spectator_button_right_y": 1055, # Lower-right Y
    "spectator_icon_x": 1586,         # Camera icon X
    "spectator_icon_y": 1025,         # Camera icon Y
    "spectator_text_x": 1640,         # Center of SPECTATE text X
    "spectator_text_y": 1031,         # Center of SPECTATE text Y

    # Screenshot configuration
    "use_steam_screenshots": True,     # Whether to try F12 Steam screenshots
    "steam_user_id": "1067368752",     # Your Steam user ID for screenshot path
    "game_display_mode": "Fullscreen", # Game display mode - "Fullscreen" or "Windowed"

    # Extended timeouts
    "max_wait_for_match": 180,  # Increased to 3 minutes minimum
    "spectate_button_check_interval": 2, # Seconds between spectate button checks
    
    # Failure scenario - Error popup
    "error_popup_x": 990,
    "error_popup_y": 460,
    "error_popup_ok_x": 1154,
    "error_popup_ok_y": 603,
    
    # Map selection coordinates
    "map_sigma_x": 380,
    "map_sigma_y": 430,
    "map_delta_x": 650,
    "map_delta_y": 430,
    "map_dust2_x": 920,
    "map_dust2_y": 430,
    "map_hostage_x": 1200,
    "map_hostage_y": 430
}

# Path for configuration files
home_dir = os.path.expanduser("~")
config_dir = os.path.join(home_dir, "OneDrive", "Документы", "AutoHotkey", "data")

# Try to create config directory if it doesn't exist
try:
    os.makedirs(config_dir, exist_ok=True)
    print(f"Config directory: {config_dir}")
except Exception as e:
    print(f"Error creating config directory: {e}")
    # Fallback to script directory
    config_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(config_dir, "data"), exist_ok=True)
    config_dir = os.path.join(config_dir, "data")
    print(f"Using fallback config directory: {config_dir}")

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