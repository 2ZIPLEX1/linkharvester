import cv2
import numpy as np
import os
import sys
import time
import glob
import shutil
import logging

# Configure paths
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
STEAM_SCREENSHOTS_PATH = r'C:\Program Files (x86)\Steam\userdata\1067368752\760\remote\730\screenshots'

# Configure logging
LOG_FILE = os.path.join(PROJECT_PATH, 'image_recognition.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

def get_latest_screenshot():
    """Get the most recent screenshot from Steam's screenshot folder"""
    try:
        screenshots = glob.glob(os.path.join(STEAM_SCREENSHOTS_PATH, '*.jpg'))
        
        if not screenshots:
            logging.warning("No screenshots found")
            return None
            
        latest_screenshot = max(screenshots, key=os.path.getmtime)
        
        # Only use if it's less than 5 seconds old
        if time.time() - os.path.getmtime(latest_screenshot) > 5:
            logging.warning("No recent screenshots found")
            return None
            
        return latest_screenshot
    except Exception as e:
        logging.error(f"Error getting screenshot: {str(e)}")
        return None

def detect_template(screenshot_path, template_name, threshold=None):
    """Detect a template in a screenshot"""
    try:
        # Set default thresholds for each template type
        default_thresholds = {
            "spectate_button": 0.8,
            "error_dialog": 0.7,
            "error_dialog_2": 0.7
        }
        
        # Use provided threshold or default for this template
        if threshold is None:
            threshold = default_thresholds.get(template_name, 0.7)
        
        # Read images
        img = cv2.imread(screenshot_path)
        template_path = os.path.join(TEMPLATES_PATH, f"{template_name}.jpg")
        template = cv2.imread(template_path)
        
        if img is None or template is None:
            logging.error(f"Could not read images: {screenshot_path} or {template_path}")
            return False, None
        
        # Convert to grayscale
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Match template
        result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        logging.info(f"Template match for {template_name}: {max_val} (threshold: {threshold})")
        
        # Return match result
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            # Removed the save_debug_image call
            
            return True, (center_x, center_y)
        else:
            return False, None
    except Exception as e:
        logging.error(f"Error detecting template: {str(e)}")
        return False, None

def detect_error_dialog():
    """Detect error dialog in the latest screenshot"""
    screenshot = get_latest_screenshot()
    if not screenshot:
        return False, None
    
    # Check for first error dialog template
    found, coords = detect_template(screenshot, "error_dialog", 0.7)
    if found:
        logging.info("ERROR DIALOG 1 DETECTED!")
        # Return coordinates for OK button of first error dialog
        ok_x = 1157  # Center of OK button X
        ok_y = 605   # Center of OK button Y
        return True, (ok_x, ok_y)
    
    # If first template not found, check for second error dialog template
    found, coords = detect_template(screenshot, "error_dialog_2", 0.7)
    if found:
        logging.info("ERROR DIALOG 2 DETECTED!")
        # Return coordinates for OK button of second error dialog
        ok_x = 1261  # Center of OK button X (between 1239 and 1283)
        ok_y = 685   # Center of OK button Y (between 661 and 708)
        return True, (ok_x, ok_y)
    
    return False, None

def detect_spectate_button():
    """Detect spectate button in the latest screenshot"""
    screenshot = get_latest_screenshot()
    if not screenshot:
        return False, None
    
    # Use a threshold of 0.8 for spectate button
    found, coords = detect_template(screenshot, "spectate_button", 0.8)
    if found:
        logging.info("SPECTATE BUTTON DETECTED!")
        return True, coords
    return False, None

# Main function for command-line usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cs2_detect.py [error|spectate]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "error":
        found, coords = detect_error_dialog()
        result = "1" if found else "0"
        print(f"ERROR_DETECTION_RESULT={result}")
        if found and coords:
            print(f"ERROR_COORDS={coords[0]},{coords[1]}")
            
    elif command == "spectate":
        found, coords = detect_spectate_button()
        result = "1" if found else "0"
        print(f"SPECTATE_DETECTION_RESULT={result}")
        if found and coords:
            print(f"SPECTATE_COORDS={coords[0]},{coords[1]}")
    
    else:
        print("Unknown command. Use 'error' or 'spectate'")