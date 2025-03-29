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

def detect_template(image_input, template_name, threshold=None, roi=None):
    """Detect a template in an image
    
    Args:
        image_input: Path to the screenshot image OR a numpy array of image data
        template_name: Name of the template to detect
        threshold: Matching threshold (0.0-1.0)
        roi: Region of interest (x, y, width, height) to restrict search
    """
    try:
        # Set default thresholds for each template type
        default_thresholds = {
            "spectate_button": 0.8,
            "error_dialog": 0.7,
            "error_dialog_2": 0.7,
            "error_dialog_3": 0.7
        }
        
        # Set default ROIs for each template type (if not provided)
        default_rois = {
            "spectate_button": (1577, 1008, 122, 47),
            "error_dialog": (704, 431, 512, 218),
            "error_dialog_2": (600, 350, 720, 379),
            "error_dialog_3": (704, 431, 512, 218)
        }
        
        # Use provided threshold or default for this template
        if threshold is None:
            threshold = default_thresholds.get(template_name, 0.7)
        
        # Use provided ROI or default for this template
        if roi is None:
            roi = default_rois.get(template_name, None)
        
        # Read image (either from path or use directly if provided as array)
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
        else:
            img = image_input
            
        template_path = os.path.join(TEMPLATES_PATH, f"{template_name}.jpg")
        template = cv2.imread(template_path)
        
        if img is None or template is None:
            logging.error(f"Could not read images: {'image path' if isinstance(image_input, str) else 'image data'} or {template_path}")
            return False, None
        
        # Get dimensions for logging
        img_height, img_width = img.shape[:2]
        
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
        else:
            img_roi = img
        
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
    found3, _ = detect_template(screenshot, "error_dialog_3", 0.7, error_roi)
    
    # If any error dialog was found
    if found1 or found2 or found3:
        # Determine dialog type 
        if found3:
            dialog_type = "fatal"
            logging.info("FATAL ERROR DIALOG DETECTED!")
            print("ERROR_DETECTION_RESULT=1")
            print("ERROR_TYPE=fatal")
            print("ERROR_COORDS=-1,-1")
        else:
            dialog_type = "first" if found1 else "second"
            logging.info(f"{dialog_type.upper()} ERROR DIALOG DETECTED!")
            print("ERROR_DETECTION_RESULT=1")
            print("ERROR_COORDS=-1,-1")
        
        # Log performance
        elapsed_time = time.time() - start_time
        logging.info(f"Error dialog detection took {elapsed_time:.4f} seconds with ROI")
        
        # Return special coordinates (-1, -1) to indicate Escape should be used
        return True, (-1, -1)
    
    # Log performance even when nothing found
    elapsed_time = time.time() - start_time
    print("ERROR_DETECTION_RESULT=0")
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
        
        # Then in find_t_player_row, replace the ROI processing code with:
        if lower_bound < height:
            roi_img = img[lower_bound:height, 0:width]
            
            # Search for Terrorists label directly in the ROI image
            t_found, roi_coords = detect_template(roi_img, "terrorists", 0.75)
            
            if t_found:
                # Adjust coordinates to original image space
                t_label_x, t_label_y = roi_coords
                t_label_y += lower_bound  # Add the offset for the ROI
                
                # Add correction for observed offset (-6px)
                t_first_row_x = 707
                t_first_row_y = t_label_y - 86 - 6  # Apply correction offset
                
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
        width: Width of the region (default: 200px)
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
        
        # Preprocess for better OCR
        # 1. Resize to make it larger (helps OCR)
        nickname_region_resized = cv2.resize(nickname_region, (nickname_width * 3, height * 3))
        
        # 2. Convert to grayscale
        gray = cv2.cvtColor(nickname_region_resized, cv2.COLOR_BGR2GRAY)
        
        # 3. Apply binary threshold
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Perform OCR with just the gray_standard method (removed binary_line)
        results = []
        
        # Standard OCR on grayscale (preserves spaces)
        try:
            text1 = pytesseract.image_to_string(gray, config="--oem 3 --psm 7").strip()
            results.append(("gray_standard", text1))
        except Exception as e:
            logging.error(f"OCR error with gray_standard: {str(e)}")
        
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
            
            # Clean up nickname - remove leading icon characters and spaces
            original_result = best_result
            
            # List of known icon patterns to remove from the beginning
            icon_patterns = ['@', '@&', '@�', '�', '�', '&']
            
            # First pass: remove exact icon patterns
            for pattern in icon_patterns:
                if best_result.startswith(pattern):
                    best_result = best_result[len(pattern):].lstrip()
                    logging.info(f"Removed icon pattern '{pattern}' from beginning of nickname")
                    break
            
            # Second pass: iteratively remove any special character at the beginning
            # This catches any other unusual icon patterns we haven't seen yet
            while best_result and not (best_result[0].isalnum() or best_result[0] == '[' or best_result[0] == '_'):
                removed_char = best_result[0]
                best_result = best_result[1:].lstrip()
                logging.info(f"Removed leading character '{removed_char}' from nickname")
            
            if original_result != best_result:
                logging.info(f"Cleaned nickname: '{original_result}' -> '{best_result}'")
            
            # Check if it's a bot (case insensitive)
            if best_result.upper().startswith("BOT "):
                logging.info(f"Detected a bot player: '{best_result}', marking for filtering")
                # We still return the bot name - filtering will happen at the AHK level
            
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
    
def detect_profile_button(region_x=None, region_y=None, region_width=None, region_height=None):
    """
    Detect profile button in a screenshot
    
    Args:
        region_x: X coordinate of the region to check
        region_y: Y coordinate of the region to check
        region_width: Width of the region to check
        region_height: Height of the region to check
    """
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for profile button detection")
            print("PROFILE_BUTTON_RESULT=0")
            print("PROFILE_BUTTON_ERROR=No recent screenshot found")
            return
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("PROFILE_BUTTON_RESULT=0")
            print("PROFILE_BUTTON_ERROR=Could not read screenshot")
            return
        
        # Define the region of interest (ROI) if provided
        if region_x is not None and region_y is not None and region_width is not None and region_height is not None:
            # Get image dimensions
            img_height, img_width = img.shape[:2]
            
            # Ensure coordinates are within image bounds
            region_x = max(0, min(region_x, img_width - 1))
            region_y = max(0, min(region_y, img_height - 1))
            region_width = min(region_width, img_width - region_x)
            region_height = min(region_height, img_height - region_y)
            
            # Check if region dimensions are valid
            if region_width <= 0 or region_height <= 0:
                logging.error(f"Invalid region dimensions: {region_width}x{region_height}")
                print("PROFILE_BUTTON_RESULT=0")
                print("PROFILE_BUTTON_ERROR=Invalid region dimensions")
                return
            
            # Extract the region
            roi = img[region_y:region_y+region_height, region_x:region_x+region_width]
            
            # Save the region for debugging with a unique timestamp
            timestamp = int(time.time())
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"profile_button_region_{timestamp}_{region_x}_{region_y}.png")
            cv2.imwrite(debug_path, roi)
            logging.info(f"Saved profile button region to: {debug_path}")
            
            # Use the extracted region for template matching
            result, coords = detect_template(roi, "profile-button", threshold=0.7)
        else:
            # Use whole image if no region specified
            result, coords = detect_template(img, "profile-button", threshold=0.7)
        
        # Output the result
        if result:
            logging.info(f"Profile button detected at: {coords}")
            print("PROFILE_BUTTON_RESULT=1")
            if coords:
                # If using a region, these are coordinates within the region
                if region_x is not None:
                    # Return adjusted coordinates if region was specified
                    adj_x = region_x + coords[0]
                    adj_y = region_y + coords[1]
                    print(f"PROFILE_BUTTON_COORDS={adj_x},{adj_y}")
                else:
                    print(f"PROFILE_BUTTON_COORDS={coords[0]},{coords[1]}")
        else:
            logging.info("Profile button not detected")
            print("PROFILE_BUTTON_RESULT=0")
        
    except Exception as e:
        logging.error(f"Error detecting profile button: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        print("PROFILE_BUTTON_RESULT=0")
        print(f"PROFILE_BUTTON_ERROR={str(e)}")

def extract_steam_url():
    """Extract Steam profile URL from the Steam browser using lock icon detection and OCR"""
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for URL extraction")
            print("URL_EXTRACTION_RESULT=0")
            print("URL_EXTRACTION_ERROR=No recent screenshot found")
            return
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("URL_EXTRACTION_RESULT=0")
            print("URL_EXTRACTION_ERROR=Could not read screenshot")
            return
        
        # Define the larger search region for the lock icon
        search_roi_x = 300
        search_roi_y = 150
        search_roi_width = 550
        search_roi_height = 300
        
        # Get image dimensions
        img_height, img_width = img.shape[:2]
        
        # Ensure the ROI is within image bounds
        if (search_roi_x >= img_width or search_roi_y >= img_height or 
            search_roi_x + search_roi_width > img_width or search_roi_y + search_roi_height > img_height):
            logging.error(f"Search ROI outside image bounds: {search_roi_x},{search_roi_y},{search_roi_width},{search_roi_height}")
            print("URL_EXTRACTION_RESULT=0")
            print("URL_EXTRACTION_ERROR=Search ROI outside image bounds")
            return
        
        # Extract the search region
        search_region = img[search_roi_y:search_roi_y+search_roi_height, search_roi_x:search_roi_x+search_roi_width]
        
        # Save the search region for debugging
        timestamp = int(time.time())
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        search_debug_path = os.path.join(debug_dir, f"lock_search_region_{timestamp}.png")
        cv2.imwrite(search_debug_path, search_region)
        logging.info(f"Saved lock icon search region to: {search_debug_path}")
        
        # Find the lock icon within the search region
        lock_found, lock_coords = detect_template(search_region, "lock-icon", threshold=0.7)
        
        if not lock_found:
            # Try with a lower threshold if not found initially
            logging.info("Trying lock icon detection with lower threshold (0.6)")
            lock_found, lock_coords = detect_template(search_region, "lock-icon", threshold=0.6)
            
            if not lock_found:
                logging.warning("Lock icon not found in search region")
                print("URL_EXTRACTION_RESULT=0")
                print("URL_EXTRACTION_ERROR=Lock icon not found")
                return
        
        logging.info(f"Lock icon found at coordinates within search region: {lock_coords}")
        
        # Create a visualization image showing where the lock was found
        visualization = search_region.copy()
        cv2.rectangle(visualization, 
                     (lock_coords[0] - 10, lock_coords[1] - 10), 
                     (lock_coords[0] + 20, lock_coords[1] + 20), 
                     (0, 255, 0), 2)
        viz_debug_path = os.path.join(debug_dir, f"lock_detection_visualization_{timestamp}.png")
        cv2.imwrite(viz_debug_path, visualization)
        logging.info(f"Saved lock detection visualization to: {viz_debug_path}")
        
        # Calculate the URL region relative to the lock icon
        # The URL starts 21px to the right of the lock icon's left edge
        # and 7px above the lock icon's Y position
        url_roi_x = search_roi_x + lock_coords[0] + 19
        url_roi_y = search_roi_y + lock_coords[1] - 7
        url_roi_width = 405
        url_roi_height = 16
        
        # Ensure the URL ROI is within image bounds
        if (url_roi_x >= img_width or url_roi_y >= img_height or 
            url_roi_x + url_roi_width > img_width or url_roi_y + url_roi_height > img_height):
            logging.error(f"URL ROI outside image bounds: {url_roi_x},{url_roi_y},{url_roi_width},{url_roi_height}")
            print("URL_EXTRACTION_RESULT=0")
            print("URL_EXTRACTION_ERROR=URL ROI outside image bounds")
            return
        
        # Extract the URL region
        url_region = img[url_roi_y:url_roi_y+url_roi_height, url_roi_x:url_roi_x+url_roi_width]
        
        # Resize to make it larger (helps OCR)
        url_region_resized = cv2.resize(url_region, (url_roi_width * 3, url_roi_height * 3))
        
        # Convert to grayscale
        gray = cv2.cvtColor(url_region_resized, cv2.COLOR_BGR2GRAY)
        
        # Apply binary thresholding
        binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
        
        # Store all results
        ocr_results = []
        
        # Try OCR with grayscale (worked well in testing)
        try:
            text_gray = pytesseract.image_to_string(gray, 
                                           config="--psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.:")
            text_gray = text_gray.strip()
            if text_gray:
                ocr_results.append(("gray", text_gray))
                logging.info(f"OCR gray result: '{text_gray}'")
        except Exception as e:
            logging.error(f"OCR gray error: {str(e)}")
        
        # Try OCR with binary thresholding as backup
        try:
            text_binary = pytesseract.image_to_string(binary, 
                                           config="--psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.:")
            text_binary = text_binary.strip()
            if text_binary:
                ocr_results.append(("binary", text_binary))
                logging.info(f"OCR binary result: '{text_binary}'")
        except Exception as e:
            logging.error(f"OCR binary error: {str(e)}")
        
        if not ocr_results:
            logging.warning("No OCR results found for URL")
            print("URL_EXTRACTION_RESULT=0")
            print("URL_EXTRACTION_ERROR=No OCR results")
            return
        
        # Validate and select the best result
        steam_urls = []
        
        for method, text in ocr_results:
            # Clean up the text to look for a valid Steam URL
            cleaned_text = text.replace(" ", "").replace("\n", "").replace("\r", "")
            
            # Check if it looks like a Steam URL
            if "steamcommunity.com" in cleaned_text.lower():
                steam_urls.append((method, cleaned_text))
        
        if steam_urls:
            # Sort by length (longer URLs are likely more complete)
            steam_urls.sort(key=lambda x: len(x[1]), reverse=True)
            
            best_url = steam_urls[0][1]
            best_method = steam_urls[0][0]
            
            # Ensure the URL ends with a slash
            if not best_url.endswith('/'):
                best_url += '/'
                logging.info(f"Added missing slash to URL: {best_url}")
            
            logging.info(f"Found valid Steam URL ({best_method}): {best_url}")
            print("URL_EXTRACTION_RESULT=1")
            print(f"URL={best_url}")
            return
        
        logging.warning("Could not find a valid Steam URL")
        print("URL_EXTRACTION_RESULT=0")
        print("URL_EXTRACTION_ERROR=No valid URL found")
        
    except Exception as e:
        logging.error(f"Error extracting Steam URL: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        print("URL_EXTRACTION_RESULT=0")
        print(f"URL_EXTRACTION_ERROR={str(e)}")

def detect_medals(roi_x, roi_y, roi_width, roi_height):
    """
    Detect medals in a specified ROI using template matching
    
    Args:
        roi_x: X-coordinate of the top-left corner of the ROI
        roi_y: Y-coordinate of the top-left corner of the ROI
        roi_width: Width of the ROI
        roi_height: Height of the ROI
    """
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for medal detection")
            print("MEDAL_DETECTION_RESULT=0")
            print("MEDAL_DETECTION_ERROR=No recent screenshot found")
            return
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("MEDAL_DETECTION_RESULT=0")
            print("MEDAL_DETECTION_ERROR=Could not read screenshot")
            return
        
        # Get image dimensions
        img_height, img_width = img.shape[:2]
        
        # Ensure ROI is within image bounds
        roi_x = max(0, min(roi_x, img_width - 1))
        roi_y = max(0, min(roi_y, img_height - 1))
        roi_width = min(roi_width, img_width - roi_x)
        roi_height = min(roi_height, img_height - roi_y)
        
        # Check if ROI dimensions are valid
        if roi_width <= 0 or roi_height <= 0:
            logging.error(f"Invalid ROI dimensions: {roi_width}x{roi_height}")
            print("MEDAL_DETECTION_RESULT=0")
            print("MEDAL_DETECTION_ERROR=Invalid ROI dimensions")
            return
        
        # Extract the ROI
        roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
        
        # Save the ROI for debugging
        timestamp = int(time.time())
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"medal_roi_{timestamp}.png")
        cv2.imwrite(debug_path, roi)
        logging.info(f"Saved medal ROI to: {debug_path}")
        
        # List of medal templates to check
        medal_templates = [
            "5-year-veteran-coin",
            "10-year-veteran-coin",
            "global-offensive-badge",
            "loyalty-badge",
            "premier-season-one-medal",
            "shanghai-2024-silver-coin",
            "10-year-birthday-coin",
            "2015-service-medal",
            "2018-service-medal",
            "2019-service-medal",
            "2020-service-medal",
            "2021-service-medal",
            "2023-service-medal",
            "2024-service-medal",
            "2025-service-medal"
        ]
        
        # Dictionary to store detection results
        detected_medals = {}
        medal_count = 0
        
        # Prepare visualization image for debugging
        visualization = roi.copy()
        
        # Process each medal template
        for template_name in medal_templates:
            # Define template path in the medals subfolder
            template_path = os.path.join(TEMPLATES_PATH, "medals", f"{template_name}.jpg")
            
            # Check if template file exists
            if not os.path.exists(template_path):
                logging.warning(f"Medal template not found: {template_path}")
                continue
                
            # Read template
            template = cv2.imread(template_path)
            if template is None:
                logging.warning(f"Could not read medal template: {template_path}")
                continue
                
            # Convert to grayscale
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Check template size vs ROI size
            template_h, template_w = template_gray.shape
            roi_h, roi_w = roi_gray.shape
            
            if template_h > roi_h or template_w > roi_w:
                logging.warning(f"Template {template_name} ({template_w}x{template_h}) is larger than ROI ({roi_w}x{roi_h})")
                continue
            
            # Perform template matching with multiple thresholds
            thresholds = [0.85, 0.80, 0.75]  # Start with high confidence threshold
            
            for threshold in thresholds:
                # Perform template matching
                result = cv2.matchTemplate(roi_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                
                # Find locations where match quality exceeds the threshold
                locations = np.where(result >= threshold)
                
                # If we have some matches, process them
                if len(locations[0]) > 0:
                    # Group close matches using non-maximum suppression
                    rectangles = []
                    for pt in zip(*locations[::-1]):  # Switch columns and rows
                        rectangles.append((pt[0], pt[1], template_w, template_h))
                    
                    # Convert to numpy array for easier processing
                    rectangles = np.array(rectangles)
                    
                    # Perform non-maximum suppression to avoid duplicate detections
                    # A simple approach: if rectangles overlap significantly, count only one
                    if len(rectangles) > 0:
                        picked_rectangles = []
                        for rect in rectangles:
                            overlap = False
                            for picked_rect in picked_rectangles:
                                # Calculate intersection over union (IOU)
                                x1 = max(rect[0], picked_rect[0])
                                y1 = max(rect[1], picked_rect[1])
                                x2 = min(rect[0] + rect[2], picked_rect[0] + picked_rect[2])
                                y2 = min(rect[1] + rect[3], picked_rect[1] + picked_rect[3])
                                
                                if x2 > x1 and y2 > y1:
                                    intersection = (x2 - x1) * (y2 - y1)
                                    union = rect[2] * rect[3] + picked_rect[2] * picked_rect[3] - intersection
                                    iou = intersection / union
                                    
                                    if iou > 0.3:  # If IOU > 30%, consider as duplicate
                                        overlap = True
                                        break
                            
                            if not overlap:
                                picked_rectangles.append(rect)
                    
                        # Add unique matches to the result
                        for rect in picked_rectangles:
                            x, y, w, h = rect
                            medal_count += 1
                            detected_medals[f"{template_name}_{medal_count}"] = {
                                "name": template_name,
                                "x": x + roi_x,  # Convert back to original image coordinates
                                "y": y + roi_y,
                                "confidence": float(result[y, x])
                            }
                            
                            # Draw on visualization image
                            cv2.rectangle(visualization, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(visualization, template_name, (x, y - 5), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # Break after finding matches at this threshold
                    break
        
        # Save visualization for debugging
        viz_path = os.path.join(debug_dir, f"medal_detection_viz_{timestamp}.png")
        cv2.imwrite(viz_path, visualization)
        logging.info(f"Saved medal detection visualization to: {viz_path}")
        
        # Output detection results
        print("MEDAL_DETECTION_RESULT=1")
        print(f"MEDAL_COUNT={len(detected_medals)}")
        
        for key, info in detected_medals.items():
            print(f"MEDAL_DETECTED={info['name']}")
            print(f"MEDAL_COORDS={info['x']},{info['y']}")
            print(f"MEDAL_CONFIDENCE={info['confidence']:.4f}")
        
        logging.info(f"Detected {len(detected_medals)} medals in the ROI")
        
    except Exception as e:
        logging.error(f"Error detecting medals: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        print("MEDAL_DETECTION_RESULT=0")
        print(f"MEDAL_DETECTION_ERROR={str(e)}")

def detect_medal_arrow():
    """Detect the right-arrow that loads more medals"""
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for medal arrow detection")
            print("MEDAL_ARROW_RESULT=0")
            print("MEDAL_ARROW_ERROR=No recent screenshot found")
            return
        
        # Define the arrow ROI
        arrow_roi_x = 1100
        arrow_roi_y = 307
        arrow_roi_width = 26
        arrow_roi_height = 21
        
        # Use the extracted region for template matching
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("MEDAL_ARROW_RESULT=0")
            print("MEDAL_ARROW_ERROR=Could not read screenshot")
            return
            
        # Ensure coordinates are within image bounds
        img_height, img_width = img.shape[:2]
        if (arrow_roi_x >= img_width or arrow_roi_y >= img_height or 
            arrow_roi_x + arrow_roi_width > img_width or arrow_roi_y + arrow_roi_height > img_height):
            logging.error(f"Arrow ROI outside image bounds: {arrow_roi_x},{arrow_roi_y},{arrow_roi_width},{arrow_roi_height}")
            print("MEDAL_ARROW_RESULT=0")
            print("MEDAL_ARROW_ERROR=Arrow ROI outside image bounds")
            return
            
        # Extract the region
        arrow_region = img[arrow_roi_y:arrow_roi_y+arrow_roi_height, arrow_roi_x:arrow_roi_x+arrow_roi_width]
        
        # Save the region for debugging
        timestamp = int(time.time())
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"medal_arrow_region_{timestamp}.png")
        cv2.imwrite(debug_path, arrow_region)
        
        # Detect template
        result, coords = detect_template(arrow_region, "right-arrow", threshold=0.7)
        
        # Output the result
        if result:
            logging.info("Medal right-arrow detected")
            print("MEDAL_ARROW_RESULT=1")
            print("MEDAL_ARROW_PRESENT=1")
        else:
            logging.info("Medal right-arrow not detected")
            print("MEDAL_ARROW_RESULT=1")
            print("MEDAL_ARROW_PRESENT=0")
            
    except Exception as e:
        logging.error(f"Error detecting medal arrow: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        print("MEDAL_ARROW_RESULT=0")
        print(f"MEDAL_ARROW_ERROR={str(e)}")

def analyze_profile(click_x, click_y):
    """
    Unified profile analysis function that performs all detection steps in a single call.
    This function analyzes the entire profile details region based on the original click coordinates.
    
    Args:
        click_x: X-coordinate of original click position on player in scoreboard
        click_y: Y-coordinate of original click position on player in scoreboard
        
    Returns:
        Complete analysis with decision on whether to proceed with Steam profile check
    """
    try:
        # Define the entire profile details ROI relative to click position
        roi_x = click_x + 28
        roi_y = click_y - 150
        roi_width = 384
        roi_height = 413
        
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
        if not screenshot_path:
            logging.warning("No recent screenshot found for profile analysis")
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=No recent screenshot found")
            return
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=Could not read screenshot")
            return
        
        # Get image dimensions
        img_height, img_width = img.shape[:2]
        
        # Ensure ROI is within image bounds
        roi_x = max(0, min(roi_x, img_width - 1))
        roi_y = max(0, min(roi_y, img_height - 1))
        roi_width = min(roi_width, img_width - roi_x)
        roi_height = min(roi_height, img_height - roi_y)
        
        # Check if ROI dimensions are valid
        if roi_width <= 0 or roi_height <= 0:
            logging.error(f"Invalid ROI dimensions: {roi_width}x{roi_height}")
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=Invalid ROI dimensions")
            return
        
        # Extract the full profile details ROI
        profile_roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
        
        # Save the unified ROI
        timestamp = int(time.time())
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save the unified ROI
        roi_debug_path = os.path.join(debug_dir, f"profile_full_roi_{timestamp}.png")
        cv2.imwrite(roi_debug_path, profile_roi)
        logging.info(f"Saved full profile ROI to: {roi_debug_path}")
        
        # Save the original screenshot with ROI highlighted
        debug_img = img.copy()
        cv2.rectangle(debug_img, (roi_x, roi_y), (roi_x+roi_width, roi_y+roi_height), (0, 255, 0), 2)
        cv2.putText(debug_img, "Unified Profile ROI", (roi_x, roi_y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        full_debug_path = os.path.join(debug_dir, f"unified_roi_full_screenshot_{timestamp}.png")
        cv2.imwrite(full_debug_path, debug_img)
        logging.info(f"Saved full screenshot with unified ROI highlighted to: {full_debug_path}")
        
        # Create a visualization image for our detections
        visualization = profile_roi.copy()
        
        # ------------- STEP 1: Check for profile button -------------
        # Look for the profile button icon across the entire ROI
        profile_button_found = False
        profile_button_x = 0
        profile_button_y = 0

        # Template matching for profile button icon using the full ROI
        template_path = os.path.join(TEMPLATES_PATH, "profile-button.jpg")
        
        # Enhanced template matching diagnostics
        if os.path.exists(template_path):
            template = cv2.imread(template_path)
            if template is not None:
                # Save template for reference
                template_debug_path = os.path.join(debug_dir, f"profile_button_template_{timestamp}.png")
                cv2.imwrite(template_debug_path, template)
                logging.info(f"Saved template image to: {template_debug_path}")
                
                logging.info(f"Template dimensions: {template.shape}")
                logging.info(f"Full ROI dimensions: {profile_roi.shape}")
                
                # Try multiple methods for diagnostics
                methods = [
                    ('TM_CCOEFF_NORMED', cv2.TM_CCOEFF_NORMED),
                    ('TM_CCORR_NORMED', cv2.TM_CCORR_NORMED),
                    ('TM_SQDIFF_NORMED', cv2.TM_SQDIFF_NORMED)
                ]
                
                # Convert to grayscale once
                full_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # Try each method for diagnostics
                for method_name, method in methods:
                    # Perform template matching
                    result = cv2.matchTemplate(full_gray, template_gray, method)
                    
                    # Get min/max values
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # For TM_SQDIFF_NORMED, smaller values are better
                    if method == cv2.TM_SQDIFF_NORMED:
                        match_val = 1.0 - min_val
                        best_loc = min_loc
                    else:
                        match_val = max_val
                        best_loc = max_loc
                    
                    logging.info(f"Method {method_name}: Best match value = {match_val:.4f}")
                    
                    # Create a heatmap for visualization
                    result_norm = result.copy()
                    if method == cv2.TM_SQDIFF_NORMED:
                        result_norm = 1.0 - result_norm
                        
                    # Normalize to 0-1 range and create heatmap
                    result_norm = cv2.normalize(result_norm, None, 0, 1, cv2.NORM_MINMAX)
                    result_heatmap = cv2.applyColorMap((result_norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
                    
                    # Save heatmap
                    heatmap_path = os.path.join(debug_dir, f"heatmap_{method_name}_{timestamp}.png")
                    cv2.imwrite(heatmap_path, result_heatmap)
                    logging.info(f"Saved heatmap for {method_name} to: {heatmap_path}")
                
                # Now do the actual detection with multiple methods and thresholds
                detect_methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_SQDIFF_NORMED]
                thresholds = [0.7, 0.6, 0.5, 0.4]  # Try progressively lower thresholds
                
                # Try each method and threshold for actual detection
                for method in detect_methods:
                    if profile_button_found:
                        break
                        
                    for threshold in thresholds:
                        if profile_button_found:
                            break
                            
                        # Perform template matching
                        result = cv2.matchTemplate(full_gray, template_gray, method)
                        
                        # For SQDIFF methods, smaller values = better matches
                        if method == cv2.TM_SQDIFF_NORMED:
                            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                            match_val = 1.0 - min_val  # Convert to a similarity score
                            match_loc = min_loc
                            logging.info(f"SQDIFF method match value: {match_val:.3f} (threshold: {threshold})")
                        else:
                            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                            match_val = max_val
                            match_loc = max_loc
                            logging.info(f"Method {method} match value: {match_val:.3f} (threshold: {threshold})")
                        
                        if ((method == cv2.TM_SQDIFF_NORMED and match_val >= threshold) or 
                            (method != cv2.TM_SQDIFF_NORMED and match_val >= threshold)):
                            h, w = template.shape[:2]
                            # Calculate coordinates relative to full image
                            profile_button_x = roi_x + match_loc[0] + w//2
                            profile_button_y = roi_y + match_loc[1] + h//2
                            profile_button_found = True
                            
                            # Draw on visualization
                            cv2.rectangle(visualization, 
                                        (match_loc[0], match_loc[1]),
                                        (match_loc[0] + w, match_loc[1] + h),
                                        (0, 255, 0), 2)
                            cv2.putText(visualization, f"Profile Button ({match_val:.2f})", 
                                    (match_loc[0], match_loc[1] - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            
                            logging.info(f"Profile button found at {profile_button_x},{profile_button_y} with confidence {match_val:.3f}")
                            break
            else:
                logging.warning(f"Failed to load template image: {template_path}")
        else:
            logging.warning(f"Profile button template not found at: {template_path}")

        # If no profile button found, try with a simple color-based detection approach as a fallback
        if not profile_button_found:
            logging.info("Template matching failed. Trying simple icon detection as a fallback.")
            
            # Convert to HSV color space for better color filtering
            hsv = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2HSV)
            
            # Define range for white/light gray (common color for profile icons)
            lower_gray = np.array([0, 0, 180])
            upper_gray = np.array([180, 30, 255])
            
            # Threshold the HSV image to get only white/light areas
            mask = cv2.inRange(hsv, lower_gray, upper_gray)
            
            # Save the mask for debugging
            mask_path = os.path.join(debug_dir, f"profile_button_mask_{timestamp}.png")
            cv2.imwrite(mask_path, mask)
            
            # Find contours in the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size (profile button should be a reasonable size)
            filtered_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                # Adjust these thresholds based on your button's actual size
                if 50 < area < 500:  
                    x, y, w, h = cv2.boundingRect(contour)
                    # Filter by aspect ratio (profile icons are approximately square)
                    aspect_ratio = float(w) / h
                    if 0.7 < aspect_ratio < 1.3:
                        filtered_contours.append((x, y, w, h, area))
            
            # Sort by area (largest first)
            filtered_contours.sort(key=lambda x: x[4], reverse=True)
            
            # Draw the contours on a debug image
            contour_img = profile_roi.copy()
            for i, (x, y, w, h, area) in enumerate(filtered_contours[:5]):  # Show top 5
                color = (0, 255, 0) if i == 0 else (0, 0, 255)
                cv2.rectangle(contour_img, (x, y), (x + w, y + h), color, 2)
                cv2.putText(contour_img, f"{i+1}: {area:.1f}", (x, y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Save the contour image
            contour_path = os.path.join(debug_dir, f"profile_button_contours_{timestamp}.png")
            cv2.imwrite(contour_path, contour_img)
            
            # If we found any potential buttons, use the largest one
            if filtered_contours:
                x, y, w, h, area = filtered_contours[0]
                profile_button_x = roi_x + x + w//2
                profile_button_y = roi_y + y + h//2
                profile_button_found = True
                
                # Draw on visualization
                cv2.rectangle(visualization, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(visualization, f"Profile Button (contour: {area:.1f})", 
                        (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                logging.info(f"Profile button found using contour method at {profile_button_x},{profile_button_y}")

        # If no profile button found, exit early
        if not profile_button_found:
            logging.info("No profile button detected in profile details")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=0")
            print("DECISION=SKIP")
            
            # Save visualization anyway for debugging
            viz_debug_path = os.path.join(debug_dir, f"profile_analysis_viz_{timestamp}.png")
            cv2.imwrite(viz_debug_path, visualization)
            return
            
        logging.info(f"Profile button found at {profile_button_x},{profile_button_y}")
        print("PROFILE_BUTTON_FOUND=1")
        print(f"PROFILE_BUTTON_COORDS={profile_button_x},{profile_button_y}")
        
        # ------------- STEP 2: Detect medals -------------
        # Look for medals across the entire ROI
        
        # List of medal templates to check
        medal_templates = [
            "5-year-veteran-coin",
            "10-year-veteran-coin",
            "global-offensive-badge",
            "loyalty-badge",
            "premier-season-one-medal",
            "shanghai-2024-silver-coin",
            "10-year-birthday-coin",
            "2015-service-medal",
            "2018-service-medal",
            "2019-service-medal",
            "2020-service-medal",
            "2021-service-medal",
            "2023-service-medal",
            "2024-service-medal",
            "2025-service-medal"
        ]
        
        # Dictionary to store detected medals
        detected_medals = {}
        
        # Flag for 5-year veteran coin
        has_5year_coin = False
        
        # Convert profile ROI to grayscale once for all medal detections
        profile_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        
        # Process each medal template
        for template_name in medal_templates:
            # Define template path in the medals subfolder
            template_path = os.path.join(TEMPLATES_PATH, "medals", f"{template_name}.jpg")
            
            # Check if template file exists
            if not os.path.exists(template_path):
                logging.warning(f"Medal template not found: {template_path}")
                continue
                
            # Read template
            template = cv2.imread(template_path)
            if template is None:
                logging.warning(f"Could not read medal template: {template_path}")
                continue
                
            # Convert to grayscale
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Check template size vs ROI size
            template_h, template_w = template_gray.shape
            if template_h > profile_gray.shape[0] or template_w > profile_gray.shape[1]:
                logging.warning(f"Template {template_name} too large for ROI")
                continue
            
            # Perform template matching with multiple thresholds
            thresholds = [0.85, 0.80, 0.75]  # Start with high confidence
            
            for threshold in thresholds:
                # Perform template matching
                result = cv2.matchTemplate(profile_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                
                # Find locations where match quality exceeds the threshold
                locations = np.where(result >= threshold)
                
                # If we have matches, process them
                if len(locations[0]) > 0:
                    # Group close matches using non-maximum suppression
                    rectangles = []
                    for pt in zip(*locations[::-1]):  # Switch columns and rows
                        rectangles.append((pt[0], pt[1], template_w, template_h))
                    
                    # Convert to numpy array for easier processing
                    rectangles = np.array(rectangles)
                    
                    # Perform non-maximum suppression to avoid duplicates
                    if len(rectangles) > 0:
                        picked_rectangles = []
                        for rect in rectangles:
                            overlap = False
                            for picked_rect in picked_rectangles:
                                # Calculate intersection over union (IOU)
                                x1 = max(rect[0], picked_rect[0])
                                y1 = max(rect[1], picked_rect[1])
                                x2 = min(rect[0] + rect[2], picked_rect[0] + picked_rect[2])
                                y2 = min(rect[1] + rect[3], picked_rect[1] + picked_rect[3])
                                
                                if x2 > x1 and y2 > y1:
                                    intersection = (x2 - x1) * (y2 - y1)
                                    union = rect[2] * rect[3] + picked_rect[2] * picked_rect[3] - intersection
                                    iou = intersection / union
                                    
                                    if iou > 0.3:  # If IOU > 30%, consider as duplicate
                                        overlap = True
                                        break
                            
                            if not overlap:
                                picked_rectangles.append(rect)
                    
                        # Add unique matches to the result
                        for i, rect in enumerate(picked_rectangles):
                            x, y, w, h = rect
                            confidence = float(result[y, x])
                            
                            detected_medals[f"{template_name}_{i}"] = {
                                "name": template_name,
                                "x": x,
                                "y": y,
                                "confidence": confidence
                            }
                            
                            # Check if this is the 5-year veteran coin
                            if template_name == "5-year-veteran-coin":
                                has_5year_coin = True
                                logging.info(f"5-year veteran coin detected with confidence {confidence:.3f}")
                            
                            # Draw on visualization
                            cv2.rectangle(visualization, 
                                         (x, y),
                                         (x + w, y + h),
                                         (0, 255, 0), 2)
                            cv2.putText(visualization, f"{template_name} ({confidence:.2f})", 
                                       (x, y - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    # Break after finding matches at this threshold
                    break
        
        # ------------- STEP 3: Check for medal arrow -------------
        # Look for the right arrow across the entire ROI
        has_more_medals = False
        arrow_template_path = os.path.join(TEMPLATES_PATH, "right-arrow.jpg")
        
        if os.path.exists(arrow_template_path):
            arrow_template = cv2.imread(arrow_template_path)
            if arrow_template is not None:
                arrow_template_gray = cv2.cvtColor(arrow_template, cv2.COLOR_BGR2GRAY)
                
                # Check if template fits in ROI
                if (arrow_template_gray.shape[0] <= profile_gray.shape[0] and
                    arrow_template_gray.shape[1] <= profile_gray.shape[1]):
                    
                    # Perform template matching
                    arrow_result = cv2.matchTemplate(profile_gray, arrow_template_gray, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(arrow_result)
                    
                    logging.info(f"Medal arrow match confidence: {max_val:.3f}")
                    
                    if max_val >= 0.7:  # Adjust threshold as needed
                        has_more_medals = True
                        h, w = arrow_template.shape[:2]
                        
                        # Draw on visualization
                        cv2.rectangle(visualization, 
                                     (max_loc[0], max_loc[1]),
                                     (max_loc[0] + w, max_loc[1] + h),
                                     (0, 255, 0), 2)
                        cv2.putText(visualization, f"More Medals ({max_val:.2f})", 
                                   (max_loc[0], max_loc[1] - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        
                        logging.info("More medals arrow detected")
        
        # ------------- STEP 4: Make decision -------------
        # Count total medals
        medal_count = len(detected_medals)
        
        # Decision criteria:
        # 1. Has 5-year veteran coin
        # 2. Has at least 4 medals total
        meets_criteria = has_5year_coin and medal_count >= 4
        
        # Save the visualization with analysis results
        viz_debug_path = os.path.join(debug_dir, f"profile_analysis_viz_{timestamp}.png")
        cv2.imwrite(viz_debug_path, visualization)
        
        # Output results
        print("PROFILE_ANALYSIS_RESULT=1")
        print(f"MEDAL_COUNT={medal_count}")
        print(f"HAS_5YEAR_COIN={1 if has_5year_coin else 0}")
        print(f"HAS_MORE_MEDALS={1 if has_more_medals else 0}")
        print(f"MEETS_CRITERIA={1 if meets_criteria else 0}")
        
        # Include individual medal information
        for key, info in detected_medals.items():
            print(f"MEDAL_DETECTED={info['name']}")
        
        # Final decision
        if meets_criteria:
            print("DECISION=PROCEED")
        else:
            print("DECISION=SKIP")
        
        logging.info(f"Profile analysis complete: {medal_count} medals, 5-year coin: {has_5year_coin}, " +
                    f"Decision: {'PROCEED' if meets_criteria else 'SKIP'}")
        
    except Exception as e:
        logging.error(f"Error in profile analysis: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        print("PROFILE_ANALYSIS_RESULT=0")
        print(f"PROFILE_ANALYSIS_ERROR={str(e)}")
        print("DECISION=SKIP")  # Default to skip on error

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
    
    elif command == "analyze_profile":
        # Check if click coordinates were provided
        if len(sys.argv) > 3:
            try:
                click_x = int(sys.argv[2])
                click_y = int(sys.argv[3])
                analyze_profile(click_x, click_y)
            except (ValueError, IndexError) as e:
                logging.error(f"Invalid click coordinates: {e}")
                print("PROFILE_ANALYSIS_RESULT=0")
                print(f"PROFILE_ANALYSIS_ERROR=Invalid click coordinates: {e}")
                print("DECISION=SKIP")
        else:
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=Missing click coordinates")
            print("DECISION=SKIP")
    
    elif command == "detect_medals":
        # Check if ROI parameters were provided
        if len(sys.argv) > 5:
            try:
                roi_x = int(sys.argv[2])
                roi_y = int(sys.argv[3])
                roi_width = int(sys.argv[4])
                roi_height = int(sys.argv[5])
                detect_medals(roi_x, roi_y, roi_width, roi_height)
            except (ValueError, IndexError) as e:
                logging.error(f"Invalid ROI parameters: {e}")
                print("MEDAL_DETECTION_RESULT=0")
                print(f"MEDAL_DETECTION_ERROR=Invalid ROI parameters: {e}")
        else:
            print("MEDAL_DETECTION_RESULT=0")
            print("MEDAL_DETECTION_ERROR=Missing ROI parameters")
            
    elif command == "detect_medal_arrow":
        detect_medal_arrow()
    
    elif command == "profile_button":
        # Check if region parameters were provided
        if len(sys.argv) > 5:
            try:
                region_x = int(sys.argv[2])
                region_y = int(sys.argv[3])
                region_width = int(sys.argv[4])
                region_height = int(sys.argv[5])
                detect_profile_button(region_x, region_y, region_width, region_height)
            except (ValueError, IndexError) as e:
                logging.error(f"Invalid region parameters: {e}")
                print("PROFILE_BUTTON_RESULT=0")
                print(f"PROFILE_BUTTON_ERROR=Invalid region parameters: {e}")
        else:
            # Use whole image if no region specified
            detect_profile_button()
    
    elif command == "extract_url":
        extract_steam_url()

    else:
        print("Unknown command. Use 'error', 'spectate', 'ct', 't', or 'benchmark'")