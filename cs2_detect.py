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

def find_ct_player_row():
    """Find only the CT player row coordinates"""
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for CT detection")
            print("CT_DETECTION_RESULT=0")
            return
        
        # Find CT label in the image
        ct_found, ct_coords = detect_template(screenshot_path, "counter-terrorists", 0.80)
        
        if ct_found:
            ct_label_x, ct_label_y = ct_coords
            
            # Add correction for observed offset (-18px)
            ct_first_row_x = 707
            ct_first_row_y = ct_label_y - 86 - 18  # Apply correction offset
            
            logging.info(f"COUNTER-TERRORISTS label found at {ct_label_x}, {ct_label_y}")
            logging.info(f"CT first player row at {ct_first_row_x}, {ct_first_row_y} (with correction)")
            
            # Output ONLY CT information
            print("CT_DETECTION_RESULT=1")
            print(f"CT_ROW_X={ct_first_row_x}")
            print(f"CT_ROW_Y={ct_first_row_y}")
        else:
            logging.warning("Counter-Terrorists label not found")
            print("CT_DETECTION_RESULT=0")
            
    except Exception as e:
        logging.error(f"Error finding CT player row: {str(e)}")
        print("CT_DETECTION_RESULT=0")
        print(f"ERROR_MESSAGE={str(e)}")

def find_t_player_row():
    """Find only the T player row coordinates"""
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for T detection")
            print("T_DETECTION_RESULT=0")
            return
        
        # Find T label in the image - we need to find CT first to determine search area
        ct_found, ct_coords = detect_template(screenshot_path, "counter-terrorists", 0.80)
        
        if not ct_found:
            logging.warning("Counter-Terrorists label not found (needed for T region)")
            print("T_DETECTION_RESULT=0")
            return
            
        # We found CT, now search for T in the lower part of the image
        ct_label_x, ct_label_y = ct_coords
        img = cv2.imread(screenshot_path)
        height, width = img.shape[:2]
        lower_bound = ct_label_y + 100  # At least 100px below the CT label
        
        # Create ROI from bottom part of the image
        if lower_bound < height:
            roi_img = img[lower_bound:height, 0:width]
            
            # Create a temporary file for the ROI
            TEMP_PATH = os.path.join(PROJECT_PATH, 'recognition', 'temp')
            os.makedirs(TEMP_PATH, exist_ok=True)
            temp_roi_path = os.path.join(TEMP_PATH, "temp_roi.jpg")
            cv2.imwrite(temp_roi_path, roi_img)
            
            # Search for Terrorists label only in the ROI
            t_found, roi_coords = detect_template(temp_roi_path, "terrorists", 0.75)
            
            if t_found:
                # Adjust coordinates to original image space
                t_label_x, t_label_y = roi_coords
                t_label_y += lower_bound  # Add the offset for the ROI
                
                # Add correction for observed offset (-6px)
                t_first_row_x = 707
                t_first_row_y = t_label_y - 86 - 6  # Apply correction offset
                
                logging.info(f"TERRORISTS label found at {t_label_x}, {t_label_y} (after ROI adjustment)")
                logging.info(f"T first player row at {t_first_row_x}, {t_first_row_y} (with correction)")
                
                # Output ONLY T information
                print("T_DETECTION_RESULT=1")
                print(f"T_ROW_X={t_first_row_x}")
                print(f"T_ROW_Y={t_first_row_y}")
            else:
                logging.warning("Terrorists label not found in ROI")
                print("T_DETECTION_RESULT=0")
        else:
            logging.warning("Not enough vertical space to search for Terrorists label")
            print("T_DETECTION_RESULT=0")
            
    except Exception as e:
        logging.error(f"Error finding T player row: {str(e)}")
        print("T_DETECTION_RESULT=0")
        print(f"ERROR_MESSAGE={str(e)}")

# Main function for command-line usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cs2_detect.py [error|spectate|ct|t]")
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
    
    elif command == "ct":
        find_ct_player_row()
        
    elif command == "t":
        find_t_player_row()

    else:
        print("Unknown command. Use 'error', 'spectate', 'ct', or 't'")