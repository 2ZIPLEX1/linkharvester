import cv2
import os
import sys
import time
import glob
import logging
import numpy as np
import subprocess
import re
import pytesseract

# Configure paths
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
STEAM_SCREENSHOTS_PATH = r'C:\Program Files (x86)\Steam\userdata\1067368752\760\remote\730\screenshots'

# Configure Tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

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
        if time.time() - os.path.getmtime(latest_screenshot) > 30:
            logging.warning("No recent screenshots found")
            return None
            
        return latest_screenshot
    except Exception as e:
        logging.error(f"Error getting screenshot: {str(e)}")
        return None

def detect_template(screenshot_path, template_name, threshold=None, roi=None):
    """Detect a template in a screenshot
    
    Args:
        screenshot_path: Path to the screenshot image
        template_name: Name of the template to detect
        threshold: Matching threshold (0.0-1.0)
        roi: Region of interest (x, y, width, height) to restrict search
    """
    try:
        # Set default thresholds for each template type
        default_thresholds = {
            "spectate_button": 0.8,
            "error_dialog": 0.7,
            "error_dialog_2": 0.7
        }
        
        # Set default ROIs for each template type (if not provided)
        default_rois = {
            "spectate_button": (1577, 1008, 122, 47),
            "error_dialog": (704, 431, 512, 218),
            "error_dialog_2": (600, 350, 720, 379)
        }
        
        # Use provided threshold or default for this template
        if threshold is None:
            threshold = default_thresholds.get(template_name, 0.7)
        
        # Use provided ROI or default for this template
        if roi is None:
            roi = default_rois.get(template_name, None)
        
        # Read images
        img = cv2.imread(screenshot_path)
        template_path = os.path.join(TEMPLATES_PATH, f"{template_name}.jpg")
        template = cv2.imread(template_path)
        
        if img is None or template is None:
            logging.error(f"Could not read images: {screenshot_path} or {template_path}")
            return False, None
        
        # Get dimensions for logging
        img_height, img_width = img.shape[:2]
        logging.info(f"Image dimensions: {img_width}x{img_height}")
        
        # Crop image to ROI if specified
        if roi:
            x, y, w, h = roi
            # Ensure ROI is within image bounds
            x = max(0, min(x, img_width - 1))
            y = max(0, min(y, img_height - 1))
            w = min(w, img_width - x)
            h = min(h, img_height - y)
            
            if w <= 0 or h <= 0:
                logging.error(f"Invalid ROI after bounds check: {x},{y},{w},{h}")
                return False, None
                
            img_roi = img[y:y+h, x:x+w]
            logging.info(f"Using ROI for {template_name}: {x},{y},{w},{h}")
        else:
            img_roi = img
            logging.info(f"Searching entire image for {template_name}")
        
        # Convert to grayscale
        img_gray = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Check for size mismatch
        template_h, template_w = template_gray.shape[:2]
        img_h, img_w = img_gray.shape[:2]
        if template_h > img_h or template_w > img_w:
            logging.error(f"Template ({template_w}x{template_h}) larger than search area ({img_w}x{img_h})")
            return False, None
        
        # Match template
        result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        logging.info(f"Template match for {template_name}: {max_val} (threshold: {threshold})")
        
        # Return match result
        if max_val >= threshold:
            h, w = template.shape[:2]
            # If ROI was used, adjust coordinates back to original image space
            if roi:
                center_x = x + max_loc[0] + w // 2
                center_y = y + max_loc[1] + h // 2
            else:
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
            
            logging.info(f"Found {template_name} at coordinates: {center_x},{center_y}")
            return True, (center_x, center_y)
        else:
            return False, None
    except Exception as e:
        logging.error(f"Error detecting template {template_name}: {str(e)}")
        # Log traceback for easier debugging
        import traceback
        logging.error(traceback.format_exc())
        return False, None

def detect_error_dialog():
    """Detect error dialog in the latest screenshot and dismiss with Escape key"""
    screenshot = get_latest_screenshot()
    if not screenshot:
        return False, None
    
    # Define error dialog ROI (x, y, width, height)
    error_roi = (600, 350, 720, 379)  # Using the coordinates you provided
    
    # Start timing
    start_time = time.time()
    
    # Check for any error dialog templates with ROI
    found1, _ = detect_template(screenshot, "error_dialog", 0.7, error_roi)
    found2, _ = detect_template(screenshot, "error_dialog_2", 0.7, error_roi)
    
    # If any error dialog was found
    if found1 or found2:
        dialog_type = "first" if found1 else "second"
        logging.info(f"{dialog_type.upper()} ERROR DIALOG DETECTED!")
        
        # Instead of clicking on specific coordinates, we'll return special coordinates
        # that signal the caller to press Escape instead
        
        # Log performance
        elapsed_time = time.time() - start_time
        logging.info(f"Error dialog detection took {elapsed_time:.4f} seconds with ROI")
        
        # Return special coordinates (-1, -1) to indicate Escape should be used
        return True, (-1, -1)
    
    # Log performance even when nothing found
    elapsed_time = time.time() - start_time
    logging.info(f"No error dialog detected (took {elapsed_time:.4f} seconds with ROI)")
    return False, None

def detect_spectate_button():
    """Detect spectate button in the latest screenshot"""
    screenshot = get_latest_screenshot()
    if not screenshot:
        return False, None
    
    # Define spectate button ROI (x, y, width, height)
    spectate_roi = (1577, 1008, 122, 47)
    
    # Start timing
    start_time = time.time()
    
    # Use a threshold of 0.8 for spectate button with ROI
    found, coords = detect_template(screenshot, "spectate_button", 0.8, spectate_roi)
    
    # Log result and performance
    elapsed_time = time.time() - start_time
    if found:
        logging.info(f"SPECTATE BUTTON DETECTED! Detection took {elapsed_time:.4f} seconds with ROI")
        return True, coords
    else:
        logging.info(f"Spectate button not found (took {elapsed_time:.4f} seconds with ROI)")
    
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

def extract_player_nickname(screenshot_path, x, y, width=200, height=26, team="unknown"):
    """
    Extract and recognize a player's nickname from a specified region in the screenshot
    Using simplified approach with fewer OCR methods for better performance
    
    Args:
        screenshot_path: Path to the screenshot image
        x: X-coordinate of the left edge of the region
        y: Y-coordinate of the top edge of the region
        width: Width of the region (default: 350px)
        height: Height of the region (default: 26px)
        team: Team identifier for debugging ("CT", "T", or "unknown")
        
    Returns:
        str: Recognized nickname or empty string if recognition failed
    """
    try:
        # Read image
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            return ""
            
        # Get image dimensions
        img_height, img_width = img.shape[:2]
        logging.info(f"Processing {team} player at {x},{y} in image of size {img_width}x{img_height}")
        
        # Ensure coordinates are within image bounds
        x = max(0, min(x, img_width - 1))
        y = max(0, min(y, img_height - 1))
        
        # Start from the exact row position
        nickname_x = x
        nickname_width = min(170, img_width - nickname_x)  # Capture a wide area
        
        # Ensure region dimensions are valid
        if nickname_width <= 0 or height <= 0 or nickname_x >= img_width:
            logging.error(f"Invalid region dimensions: x={nickname_x}, y={y}, w={nickname_width}, h={height}")
            return ""
        
        # Extract the nickname region
        nickname_region = img[y:y+height, nickname_x:nickname_x+nickname_width]

        # First check if the slot is empty before attempting OCR
        if is_empty_player_slot(nickname_region):
            logging.info(f"Skipping OCR - empty {team} player slot detected at {x},{y}")
            return ""
        
        # Create debug filename with team info
        timestamp = int(time.time())
        debug_filename = f"{team}_player_{timestamp}_{x}_{y}"
        
        # Save the extracted region for debugging
        debug_dir = os.path.join(PROJECT_PATH, 'recognition', 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"{debug_filename}_region.jpg")
        
        # Save the debug image
        save_success = cv2.imwrite(debug_path, nickname_region)
        if not save_success:
            logging.error(f"Failed to save debug image to {debug_path}")
            # Try to create directory again and retry save
            os.makedirs(debug_dir, exist_ok=True)
            save_success = cv2.imwrite(debug_path, nickname_region)
            logging.info(f"Retry save result: {save_success}")
        else:
            logging.info(f"Saved {team} nickname region to {debug_path}")
        
        # Preprocess for better OCR
        # 1. Resize to make it larger (helps OCR)
        nickname_region_resized = cv2.resize(nickname_region, (nickname_width * 3, height * 3))
        
        # 2. Convert to grayscale
        gray = cv2.cvtColor(nickname_region_resized, cv2.COLOR_BGR2GRAY)
        
        # 3. Apply binary threshold
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Save grayscale and binary images for debugging
        gray_debug_path = os.path.join(debug_dir, f"{debug_filename}_gray.jpg")
        cv2.imwrite(gray_debug_path, gray)
        
        binary_debug_path = os.path.join(debug_dir, f"{debug_filename}_binary.jpg")
        cv2.imwrite(binary_debug_path, binary)
        
        # Perform OCR with just 2 methods instead of 6
        results = []
        
        # Method 1: Standard OCR on grayscale (preserves spaces)
        try:
            text1 = pytesseract.image_to_string(gray, config="--oem 3 --psm 7").strip()
            results.append(("gray_standard", text1))
        except Exception as e:
            logging.error(f"OCR error with gray_standard: {str(e)}")
        
        # Method 2: Binary with character whitelist
        try:
            text2 = pytesseract.image_to_string(
                binary, 
                config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-[](){}|. "
            ).strip()
            results.append(("binary_line", text2))
        except Exception as e:
            logging.error(f"OCR error with binary_line: {str(e)}")
        
        # Log all results
        logging.info(f"OCR results for {team} region at {x},{y}:")
        for method, result in results:
            logging.info(f"  {method}: '{result}'")
        
        # Filter out empty or invalid results
        valid_results = [(method, text) for method, text in results if text and any(c.isalnum() for c in text)]
        
        if not valid_results:
            logging.warning(f"No valid OCR results found for {team} region at {x},{y}")
            return ""
        
        # Score the results with improved space handling
        scored_results = []
        for method, text in valid_results:
            # Count alphanumeric and spaces as "good" characters
            good_chars = sum(c.isalnum() or c.isspace() for c in text)
            special_count = len(text) - good_chars
            
            # Don't penalize results for having spaces
            length_score = 1.0 if 3 <= len(text) <= 24 else 0.5
            good_ratio = good_chars / len(text) if len(text) > 0 else 0
            
            # Penalize excessive special characters
            special_penalty = max(0, 1.0 - (special_count / len(text) * 2)) if len(text) > 0 else 0
            
            score = length_score * good_ratio * special_penalty
            scored_results.append((text, score, method))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Log scoring results
        for text, score, method in scored_results:
            logging.info(f"  Score {score:.2f} for '{text}' ({method})")
        
        # Take the highest scored result
        if scored_results:
            best_result = scored_results[0][0]
            logging.info(f"Selected {team} nickname: '{best_result}'")
            return best_result
        
        return ""
        
    except Exception as e:
        logging.error(f"Error extracting {team} player nickname: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return ""

def extract_ct_player_nicknames(screenshot_path=None, first_row_x=None, first_row_y=None):
    """
    Extract nicknames for Counter-Terrorist team players
    
    Args:
        screenshot_path: Path to screenshot (if None, uses latest screenshot)
        first_row_x: X-coordinate of first row (if None, detects it)
        first_row_y: Y-coordinate of first row (if None, detects it)
        
    Returns:
        list: List of dictionaries containing player information
    """
    if screenshot_path is None:
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.error("No screenshot available for nickname extraction")
            return []
    
    # If coordinates not provided, detect them
    if first_row_x is None or first_row_y is None:
        logging.info("Detecting CT team row position...")
        
        # Run CT detection
        ct_found, ct_coords = False, None
        
        # Use existing code to find CT first row coordinates
        ct_found, ct_coords = find_team_positions(screenshot_path)
        
        if not ct_found or not ct_coords or 'ct' not in ct_coords:
            logging.error("Failed to detect CT team row position")
            return []
            
        first_row_x, first_row_y = ct_coords['ct']['x'], ct_coords['ct']['y']
    
    logging.info(f"Extracting CT player nickname from position ({first_row_x}, {first_row_y})")
    
    # Extract first player nickname - pass "CT" as team identifier
    nickname = extract_player_nickname(screenshot_path, first_row_x, first_row_y, team="CT")
    
    if nickname:
        logging.info(f"Extracted CT player nickname: {nickname}")
        return [{"team": "CT", "index": 0, "nickname": nickname, "row_x": first_row_x, "row_y": first_row_y}]
    else:
        logging.warning("Failed to extract CT player nickname")
        return []

def extract_t_player_nicknames(screenshot_path=None, first_row_x=None, first_row_y=None):
    """
    Extract nicknames for Terrorist team players
    
    Args:
        screenshot_path: Path to screenshot (if None, uses latest screenshot)
        first_row_x: X-coordinate of first row (if None, detects it)
        first_row_y: Y-coordinate of first row (if None, detects it)
        
    Returns:
        list: List of dictionaries containing player information
    """
    if screenshot_path is None:
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.error("No screenshot available for nickname extraction")
            return []
    
    # If coordinates not provided, detect them
    if first_row_x is None or first_row_y is None:
        logging.info("Detecting T team row position...")
        
        # Use existing code to find T first row coordinates
        t_found, t_coords = find_team_positions(screenshot_path)
        
        if not t_found or not t_coords or 't' not in t_coords:
            logging.error("Failed to detect T team row position")
            return []
            
        first_row_x, first_row_y = t_coords['t']['x'], t_coords['t']['y']
    
    logging.info(f"Extracting T player nickname from position ({first_row_x}, {first_row_y})")
    
    # Extract first player nickname - pass "T" as team identifier
    nickname = extract_player_nickname(screenshot_path, first_row_x, first_row_y, team="T")
    
    if nickname:
        logging.info(f"Extracted T player nickname: {nickname}")
        return [{"team": "T", "index": 0, "nickname": nickname, "row_x": first_row_x, "row_y": first_row_y}]
    else:
        logging.warning("Failed to extract T player nickname")
        return []

def is_empty_player_slot(img, edge_threshold=0.015, ocr_confidence=0.3):
    """
    Check if a player slot is empty using multiple methods
    
    Args:
        img: Image region to check
        edge_threshold: Threshold for edge detection method
        ocr_confidence: Minimum confidence for OCR detection
    
    Returns:
        bool: True if slot is empty, False otherwise
    """
    # Method 1: Edge detection (your current approach but with adjustable threshold)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = cv2.countNonZero(edges) / (img.shape[0] * img.shape[1])
    logging.info(f"Edge density: {edge_density:.4f}")
    
    if edge_density > edge_threshold:
        return False  # Not empty based on edge detection
    
    # Method 2: Add basic OCR check using pytesseract
    try:
        import pytesseract
        # Improve image for OCR
        prepared = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        text = pytesseract.image_to_string(prepared)
        if text.strip():  # If any text is detected
            logging.info(f"OCR detected text: '{text.strip()}'")
            return False  # Not empty based on OCR
    except ImportError:
        logging.warning("pytesseract not available, skipping OCR check")
    
    # Method 3: Check for non-background pixels
    # Assume background is dark, text is light
    _, thresholded = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    white_pixel_ratio = cv2.countNonZero(thresholded) / (img.shape[0] * img.shape[1])
    logging.info(f"White pixel ratio: {white_pixel_ratio:.4f}")
    
    if white_pixel_ratio > 0.01:  # If more than 1% of pixels are bright
        return False
    
    # If we passed all checks, likely empty
    return True

def find_team_positions(screenshot_path):
    """
    Find both CT and T team positions in one function
    
    Returns:
        tuple: (found, positions) where positions is a dict with 'ct' and 't' keys
    """
    try:
        # Create a helper function to extract coordinates from detector output
        def extract_coords(result, prefix):
            found = False
            x, y = None, None
            
            if f"{prefix}_DETECTION_RESULT=1" in result:
                found = True
                # Extract X coordinate
                if match := re.search(f"{prefix}_ROW_X=(\\d+)", result):
                    x = int(match.group(1))
                # Extract Y coordinate
                if match := re.search(f"{prefix}_ROW_Y=(\\d+)", result):
                    y = int(match.group(1))
            
            return found, (x, y) if found and x is not None and y is not None else None
        
        # Create a temporary script to run both detections
        temp_script = """
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cs2_detect import find_ct_player_row, find_t_player_row

# First run CT detection
find_ct_player_row()
print("---SEPARATOR---")
# Then run T detection
find_t_player_row()
"""
        temp_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_team_detector.py')
        with open(temp_script_path, 'w') as f:
            f.write(temp_script)
        
        # Run the script
        cmd = [sys.executable, temp_script_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout
        
        # Split the output at the separator
        if "---SEPARATOR---" in output:
            ct_output, t_output = output.split("---SEPARATOR---", 1)
        else:
            ct_output, t_output = output, ""
        
        # Extract CT coordinates
        ct_found, ct_coords = extract_coords(ct_output, "CT")
        
        # Extract T coordinates
        t_found, t_coords = extract_coords(t_output, "T")
        
        # Clean up
        try:
            os.remove(temp_script_path)
        except Exception as e:
            logging.warning(f"Failed to remove temporary script: {str(e)}")
        
        # Prepare results
        found = ct_found or t_found
        positions = {}
        
        if ct_found and ct_coords:
            positions['ct'] = {'x': ct_coords[0], 'y': ct_coords[1]}
        
        if t_found and t_coords:
            positions['t'] = {'x': t_coords[0], 'y': t_coords[1]}
        
        return found, positions
        
    except Exception as e:
        logging.error(f"Error finding team positions: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return False, {}

def check_tesseract_available():
    """Check if Tesseract OCR is available and properly configured"""
    try:
        # Check if the Tesseract executable exists
        if not os.path.exists(TESSERACT_PATH):
            logging.error(f"Tesseract executable not found at path: {TESSERACT_PATH}")
            print(f"ERROR: Tesseract OCR not found at: {TESSERACT_PATH}")
            print("Please install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki")
            return False
            
        # Try a simple OCR test to ensure it's working
        test_img = np.zeros((50, 200), dtype=np.uint8)
        cv2.putText(test_img, "Test123", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
        
        # Save the test image
        test_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tesseract_test.jpg')
        cv2.imwrite(test_img_path, test_img)
        
        # Try to recognize text
        try:
            text = pytesseract.image_to_string(test_img_path).strip()
            os.remove(test_img_path)  # Clean up
            
            if "Test" in text:
                logging.info(f"Tesseract OCR is working correctly. Test result: '{text}'")
                return True
            else:
                logging.warning(f"Tesseract OCR returned unexpected result: '{text}'")
                print(f"WARNING: Tesseract OCR test produced unexpected result: '{text}'")
                return False
                
        except Exception as e:
            logging.error(f"Error during Tesseract OCR test: {str(e)}")
            print(f"ERROR: Tesseract OCR test failed: {str(e)}")
            return False
            
    except Exception as e:
        logging.error(f"Error checking Tesseract availability: {str(e)}")
        print(f"ERROR: Could not check Tesseract OCR: {str(e)}")
        return False

# Main function for command-line usage
if __name__ == "__main__":
    # Ensure Tesseract is available for OCR functions
    if any(cmd in sys.argv for cmd in ["nickname_ct", "nickname_t", "nicknames"]):
        if not check_tesseract_available():
            print("ERROR: Tesseract OCR is required but not properly configured.")
            print("Please install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("And ensure the path is correct in the script (TESSERACT_PATH).")
            sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python cs2_detect.py [error|spectate|ct|t|benchmark|nickname_ct|nickname_t|nicknames]")
        sys.exit(1)
        
    command = sys.argv[1].lower()

    if len(sys.argv) < 2:
        print("Usage: python cs2_detect.py [error|spectate|ct|t|benchmark]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "error":
        found, coords = detect_error_dialog()
        result = "1" if found else "0"
        print(f"ERROR_DETECTION_RESULT={result}")
        if found:
            # Always return coordinates, even if they're the special (-1, -1) value
            if coords:
                print(f"ERROR_COORDS={coords[0]},{coords[1]}")
            else:
                # Fallback if coords is None for some reason
                print(f"ERROR_COORDS=-1,-1")
            
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
    
    elif command == "nickname_ct":
        # Extract nickname for the first CT player
        if len(sys.argv) > 3:  # If coordinates are provided
            try:
                row_x = int(sys.argv[2])
                row_y = int(sys.argv[3])
                players = extract_ct_player_nicknames(None, row_x, row_y)
            except ValueError:
                print("Invalid coordinates. Use: python cs2_detect.py nickname_ct X Y")
                players = []
        else:
            players = extract_ct_player_nicknames()
        
        # Output results
        if players:
            print(f"CT_NICKNAME_RESULT=1")
            for player in players:
                print(f"CT_NICKNAME={player['nickname']}")
                print(f"CT_ROW_X={player['row_x']}")
                print(f"CT_ROW_Y={player['row_y']}")
        else:
            print(f"CT_NICKNAME_RESULT=0")

    elif command == "nickname_t":
        # Extract nickname for the first T player
        if len(sys.argv) > 3:  # If coordinates are provided
            try:
                row_x = int(sys.argv[2])
                row_y = int(sys.argv[3])
                players = extract_t_player_nicknames(None, row_x, row_y)
            except ValueError:
                print("Invalid coordinates. Use: python cs2_detect.py nickname_t X Y")
                players = []
        else:
            players = extract_t_player_nicknames()
        
        # Output results
        if players:
            print(f"T_NICKNAME_RESULT=1")
            for player in players:
                print(f"T_NICKNAME={player['nickname']}")
                print(f"T_ROW_X={player['row_x']}")
                print(f"T_ROW_Y={player['row_y']}")
        else:
            print(f"T_NICKNAME_RESULT=0")

    elif command == "nicknames":
        # Extract nicknames for both teams' first players
        screenshot = get_latest_screenshot()
        if not screenshot:
            print("No recent screenshot found. Take a screenshot with F12 and try again.")
            sys.exit(1)
        
        # First find team positions
        found, positions = find_team_positions(screenshot)
        
        if not found:
            print("Failed to detect team positions")
            print("NICKNAME_RESULT=0")
            sys.exit(1)
        
        ct_players = []
        t_players = []
        
        # Extract CT players if position found
        if 'ct' in positions:
            ct_x = positions['ct']['x']
            ct_y = positions['ct']['y']
            ct_players = extract_ct_player_nicknames(screenshot, ct_x, ct_y)
        
        # Extract T players if position found
        if 't' in positions:
            t_x = positions['t']['x']
            t_y = positions['t']['y']
            t_players = extract_t_player_nicknames(screenshot, t_x, t_y)
        
        # Output results
        if ct_players or t_players:
            print("NICKNAME_RESULT=1")
            
            for player in ct_players:
                print(f"CT_NICKNAME={player['nickname']}")
                print(f"CT_ROW_X={player['row_x']}")
                print(f"CT_ROW_Y={player['row_y']}")
            
            for player in t_players:
                print(f"T_NICKNAME={player['nickname']}")
                print(f"T_ROW_X={player['row_x']}")
                print(f"T_ROW_Y={player['row_y']}")
        else:
            print("NICKNAME_RESULT=0")

    else:
        print("Unknown command. Use 'error', 'spectate', 'ct', 't', or 'benchmark'")