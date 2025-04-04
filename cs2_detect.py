import cv2
import os
import sys
import time
import glob
import logging
import numpy as np
import pytesseract
import traceback

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
    """Extract Steam profile URL from the Steam browser using lock icon detection and OCR, and also locate tab close button"""
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
        
        # Define the larger search region for the lock icon and close button
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
        
        # Find the lock icon within the search region
        lock_found, lock_coords = detect_template(search_region, "lock-icon", threshold=0.7)
        
        # Find the tab close button (x-plus pattern)
        tab_close_found, tab_close_coords = detect_template(search_region, "x-plus", threshold=0.7)
        
        if tab_close_found:
            # Calculate absolute coordinates
            tab_close_x = search_roi_x + tab_close_coords[0]
            tab_close_y = search_roi_y + tab_close_coords[1]
            logging.info(f"Tab close button found at coordinates: {tab_close_x},{tab_close_y}")
            print(f"TAB_CLOSE_BUTTON_FOUND=1")
            print(f"TAB_CLOSE_COORDS={tab_close_x},{tab_close_y}")
        else:
            # Try with a lower threshold if not found initially
            tab_close_found, tab_close_coords = detect_template(search_region, "x-plus", threshold=0.6)
            
            if tab_close_found:
                tab_close_x = search_roi_x + tab_close_coords[0]
                tab_close_y = search_roi_y + tab_close_coords[1]
                logging.info(f"Tab close button found at coordinates: {tab_close_x},{tab_close_y}")
                print(f"TAB_CLOSE_BUTTON_FOUND=1")
                print(f"TAB_CLOSE_COORDS={tab_close_x},{tab_close_y}")
            else:
                logging.warning("Tab close button not found")
                print("TAB_CLOSE_BUTTON_FOUND=0")
        
        if not lock_found:
            # Try with a lower threshold if not found initially
            lock_found, lock_coords = detect_template(search_region, "lock-icon", threshold=0.6)
            
            if not lock_found:
                logging.warning("Lock icon not found in search region")
                print("URL_EXTRACTION_RESULT=0")
                print("URL_EXTRACTION_ERROR=Lock icon not found")
                return
        
        logging.info(f"Lock icon found at coordinates: {lock_coords}")
        
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
        logging.error(traceback.format_exc())
        print("URL_EXTRACTION_RESULT=0")
        print(f"URL_EXTRACTION_ERROR={str(e)}")

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
        print("Usage: python cs2_detect.py [command] [options]")
        print("Available commands:")
        print("  error                    - Detect error dialogs")
        print("  spectate                 - Detect spectate button")
        print("  profile_button          - Detect profile button")
        print("  extract_url             - Extract Steam profile URL")
        print("  analyze_profile x y     - Analyze player profile at coordinates (x,y)")
        print("  detect_medals x y w h   - Detect medals in region (x,y,width,height)")
        print("  detect_medal_arrow      - Detect medal arrow indicator")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    # Handle different commands
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
    
    elif command == "check_scoreboard":
        try:
            # Check if ROI parameters were provided
            if len(sys.argv) > 5:
                roi_x = int(sys.argv[2])
                roi_y = int(sys.argv[3])
                roi_width = int(sys.argv[4])
                roi_height = int(sys.argv[5])
                
                # Get the latest screenshot
                screenshot_path = get_latest_screenshot()
                if not screenshot_path:
                    print("SCOREBOARD_VISIBLE=0")
                    print("ERROR=No recent screenshot found")
                    sys.exit(1)
                
                # Read the screenshot
                img = cv2.imread(screenshot_path)
                if img is None:
                    print("SCOREBOARD_VISIBLE=0")
                    print("ERROR=Could not read screenshot")
                    sys.exit(1)
                
                # Extract the ROI
                roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
                
                # Save the ROI for debugging
                timestamp = int(time.time())
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f"scoreboard_icon_roi_{timestamp}.png")
                cv2.imwrite(debug_path, roi)
                logging.info(f"Saved scoreboard icon ROI to: {debug_path}")
                
                # Detect the valve-cs2-icon.jpg in the ROI
                template_path = os.path.join(TEMPLATES_PATH, "valve-cs2-icon.jpg")
                found, coords = detect_template(roi, "valve-cs2-icon", threshold=0.7)
                
                if found:
                    # Icon found
                    icon_y = roi_y + coords[1]  # Adjust Y coordinate to full image space
                    print("SCOREBOARD_VISIBLE=1")
                    print(f"ICON_Y={icon_y}")
                    logging.info(f"Scoreboard icon found at Y: {icon_y}")
                    
                    # Save a copy of the matched region for verification
                    template = cv2.imread(template_path)
                    h, w = template.shape[:2]
                    matched_region = roi[coords[1]-5:coords[1]+h+5, coords[0]-5:coords[0]+w+5]
                    match_path = os.path.join(debug_dir, f"scoreboard_icon_match_{timestamp}.png")
                    cv2.imwrite(match_path, matched_region)
                else:
                    # Icon not found
                    print("SCOREBOARD_VISIBLE=0")
                    logging.info("Scoreboard icon not found in ROI")
            else:
                print("SCOREBOARD_VISIBLE=0")
                print("ERROR=Missing ROI parameters")
        except Exception as e:
            print("SCOREBOARD_VISIBLE=0")
            print(f"ERROR={str(e)}")
            logging.error(f"Error checking scoreboard: {str(e)}")
            logging.error(traceback.format_exc())
    
    elif command == "analyze_profile":
        # Import the profile analyzer function
        from cs2_profile_analyzer import analyze_profile
        
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
    
    elif command == "extract_url":
        extract_steam_url()

    else:
        print(f"Unknown command: {command}")
        print("Use 'python cs2_detect.py' without arguments to see available commands.")