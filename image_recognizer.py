import os
import sys
import time
import pytesseract
import cv2
import numpy as np
from PIL import Image
import glob
import shutil
import logging

# Configure paths
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
STEAM_SCREENSHOTS_PATH = r'C:\Program Files (x86)\Steam\userdata\1067368752\760\remote\730\screenshots'
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
RECOGNITION_PATH = os.path.join(PROJECT_PATH, 'recognition')
SCREENSHOTS_PATH = os.path.join(RECOGNITION_PATH, 'screenshots')
TEMPLATES_PATH = os.path.join(RECOGNITION_PATH, 'templates')
TEMP_PATH = os.path.join(RECOGNITION_PATH, 'temp')

# Configure logging
LOG_FILE = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Документы', 'AutoHotkey', 'image_recognition.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Ensure directories exist
for path in [SCREENSHOTS_PATH, TEMPLATES_PATH, TEMP_PATH]:
    os.makedirs(path, exist_ok=True)

def get_latest_screenshot():
    """Get the most recent screenshot from Steam's screenshot folder"""
    try:
        # Find all jpg files in Steam screenshots directory
        screenshots = glob.glob(os.path.join(STEAM_SCREENSHOTS_PATH, '*.jpg'))
        
        if not screenshots:
            logging.warning("No screenshots found in Steam directory")
            return None
            
        # Get the most recent file
        latest_screenshot = max(screenshots, key=os.path.getmtime)
        
        # Only use it if it's less than 10 seconds old
        mod_time = os.path.getmtime(latest_screenshot)
        if time.time() - mod_time > 10:
            logging.warning("Latest screenshot is too old")
            return None
            
        # Copy to our screenshots directory with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        dest_path = os.path.join(SCREENSHOTS_PATH, f"screenshot_{timestamp}.jpg")
        shutil.copy2(latest_screenshot, dest_path)
        
        logging.info(f"Found and copied latest screenshot: {dest_path}")
        return dest_path
    except Exception as e:
        logging.error(f"Error getting latest screenshot: {str(e)}")
        return None

def find_template_in_image(screenshot_path, template_name, threshold=0.8):
    """Find a template image within a screenshot using template matching"""
    try:
        template_path = os.path.join(TEMPLATES_PATH, f"{template_name}.jpg")
        
        if not os.path.exists(template_path):
            logging.error(f"Template not found: {template_path}")
            return False, None
            
        # Read images
        img = cv2.imread(screenshot_path)
        template = cv2.imread(template_path)
        
        # Convert both to grayscale
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Perform template matching
        result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        
        # Get coordinates of best match
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        logging.info(f"Template matching result for {template_name}: {max_val}")
        
        # If good match found
        if max_val >= threshold:
            # Get coordinates for center of template
            h, w = template.shape[:2]
            top_left = max_loc
            center_x = top_left[0] + w//2
            center_y = top_left[1] + h//2
            
            # Draw rectangle around found template (for debugging)
            bottom_right = (top_left[0] + w, top_left[1] + h)
            cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)
            debug_path = os.path.join(TEMP_PATH, f"debug_{os.path.basename(screenshot_path)}")
            cv2.imwrite(debug_path, img)
            
            logging.info(f"Found template {template_name} at coordinates {center_x},{center_y}")
            return True, (center_x, center_y)
        else:
            logging.info(f"Template {template_name} not found")
            return False, None
    except Exception as e:
        logging.error(f"Error finding template: {str(e)}")
        return False, None

def find_text_in_image(screenshot_path, text_to_find, region=None):
    """Find specific text in a screenshot using OCR"""
    try:
        img = Image.open(screenshot_path)
        
        # Crop image if region specified
        if region:
            img = img.crop(region)  # region = (left, top, right, bottom)
        
        # Preprocess for better OCR
        img = img.convert('L')  # Convert to grayscale
        
        # Save processed image for debugging
        processed_path = os.path.join(TEMP_PATH, f"ocr_{os.path.basename(screenshot_path)}")
        img.save(processed_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(img)
        
        logging.info(f"OCR result: {text}")
        
        # Check if target text is in OCR result
        if text_to_find.lower() in text.lower():
            logging.info(f"Found text: {text_to_find}")
            return True
        else:
            logging.info(f"Text not found: {text_to_find}")
            return False
    except Exception as e:
        logging.error(f"Error performing OCR: {str(e)}")
        return False

def detect_spectate_button():
    """Detect the SPECTATE button in the latest screenshot"""
    screenshot_path = get_latest_screenshot()
    if not screenshot_path:
        return False, None
        
    # Try to find the template first
    found, coords = find_template_in_image(screenshot_path, "spectate_button")
    if found:
        return True, coords
        
    # Fallback to text detection in the bottom right region
    # Assuming 1920x1080 resolution, define bottom right region
    img = Image.open(screenshot_path)
    width, height = img.size
    bottom_right = (width - 400, height - 200, width, height)
    
    found = find_text_in_image(screenshot_path, "SPECTATE", bottom_right)
    if found:
        # Return approximate spectate button coordinates
        return True, (1640, 1031)
    
    return False, None

def detect_error_message():
    """Detect error messages in the latest screenshot"""
    screenshot_path = get_latest_screenshot()
    if not screenshot_path:
        return False, None
        
    # Try to find known error templates
    found, coords = find_template_in_image(screenshot_path, "error_dialog")
    if found:
        return True, coords
        
    # Fallback to OCR to look for error-related text in the center region
    img = Image.open(screenshot_path)
    width, height = img.size
    center_region = (width//2 - 300, height//2 - 200, width//2 + 300, height//2 + 200)
    
    error_terms = ["error", "failed", "unable", "cannot", "timeout"]
    for term in error_terms:
        found = find_text_in_image(screenshot_path, term, center_region)
        if found:
            # Return approximate OK button coordinates
            return True, (width//2, height//2 + 100)
    
    return False, None

# Testing functions
def test():
    """Run tests on the latest screenshot"""
    print("Testing image recognition functions...")
    
    screenshot_path = get_latest_screenshot()
    if not screenshot_path:
        print("No recent screenshot found. Take a screenshot with F12 and try again.")
        return
        
    print(f"Using screenshot: {screenshot_path}")
    
    # Test spectate button detection
    spectate_found, spectate_coords = detect_spectate_button()
    print(f"Spectate button detection: {spectate_found}")
    if spectate_found:
        print(f"Coordinates: {spectate_coords}")
        
    # Test error message detection
    error_found, error_coords = detect_error_message()
    print(f"Error message detection: {error_found}")
    if error_found:
        print(f"Coordinates: {error_coords}")

# Main function for command-line usage
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            test()
        elif command == "spectate":
            found, coords = detect_spectate_button()
            # Return 1 if found, 0 if not (for AHK to parse)
            print(1 if found else 0)
            if found:
                print(f"{coords[0]},{coords[1]}")
        elif command == "error":
            found, coords = detect_error_message()
            print(1 if found else 0)
            if found:
                print(f"{coords[0]},{coords[1]}")
    else:
        print("Usage: python image_recognizer.py [test|spectate|error]")