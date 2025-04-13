"""
Sympathies detection utilities for CS2 profile analysis.
These functions are meant to be imported and used by the main profile analyzer.
"""

import cv2
import os
import logging
import traceback
import pytesseract

# Configure paths
PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
SYMPATHIES_PATH = os.path.join(TEMPLATES_PATH, 'sympathies')

# Configure logging
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(root_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)
LOG_FILE = os.path.join(logs_dir, 'image_recognition.log')

# Configure Tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def ensure_logs_directory():
    """Ensure the logs directory exists."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(root_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def detect_sympathy_template(image_input, template_name, threshold=0.7, roi=None, debug_name=None):
    """Detect a sympathy icon template in an image
    
    Args:
        image_input: Path to the screenshot image OR a numpy array of image data
        template_name: Name of the template to detect
        threshold: Matching threshold (0.0-1.0)
        roi: Region of interest (x, y, width, height) to restrict search
        debug_name: Name to use for debugging images
        
    Returns:
        tuple: (found, coordinates, max_val) where coordinates is (x, y) of the center of the match
               and max_val is the confidence score
    """
    try:
        # Read image (either from path or use directly if provided as array)
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
        else:
            img = image_input
            
        template_path = os.path.join(SYMPATHIES_PATH, f"{template_name}.jpg")
        template = cv2.imread(template_path)
        
        if img is None or template is None:
            logging.error(f"Could not read images: {'image path' if isinstance(image_input, str) else 'image data'} or {template_path}")
            return False, None, 0.0
        
        # Crop image to ROI if specified
        if roi:
            x, y, w, h = roi
            img_roi = img[y:y+h, x:x+w]
        else:
            img_roi = img
        
        # REMOVED: Save ROI for debugging if debug_name provided
        # This prevents saving sympathy_crown_1743583770_roi.png etc.
        
        # Convert to grayscale
        img_gray = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Check for size mismatch
        template_h, template_w = template_gray.shape[:2]
        img_h, img_w = img_gray.shape[:2]
        if template_h > img_h or template_w > img_w:
            logging.error(f"Template ({template_w}x{template_h}) larger than search area ({img_w}x{img_h})")
            return False, None, 0.0
        
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
                
                # REMOVED: For debug visualization with debug_name
                # This prevents saving sympathy detection visualization
            else:
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
            
            logging.info(f"Found {template_name} at coordinates: {center_x},{center_y} with confidence: {max_val:.3f}")
            return True, (center_x, center_y), max_val
        else:
            return False, None, max_val
    except Exception as e:
        logging.error(f"Error detecting template {template_name}: {str(e)}")
        logging.error(traceback.format_exc())
        return False, None, 0.0

def extract_sympathy_number(img, roi_x, roi_y, roi_width, roi_height, debug_name=None):
    """Extract a number from an image region using OCR
    
    Args:
        img: Image data
        roi_x, roi_y, roi_width, roi_height: Region of interest coordinates
        debug_name: Name for debug images
        
    Returns:
        int: Extracted number or 0 if extraction failed
    """
    try:
        # Extract the region
        roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
        
        # REMOVED: Save ROI for debugging if debug_name provided
        # This prevents saving sympathy_crown_number_1743583742_number_roi.png etc.
        
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to isolate the text
        _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
        
        # REMOVED: Save thresholded image for debugging
        # This prevents saving sympathy number threshold images
        
        # Scale up the image for better OCR (3x)
        scaled = cv2.resize(thresh, (roi_width * 3, roi_height * 3), interpolation=cv2.INTER_CUBIC)
        
        # Use Tesseract to extract the number with specific config for digits
        text = pytesseract.image_to_string(scaled, 
                                       config="--psm 7 -c tessedit_char_whitelist=0123456789")
        
        # Clean the text and convert to integer
        text = text.strip()
        logging.info(f"OCR extracted text: '{text}' from {debug_name}")
        
        if text.isdigit():
            return int(text)
        else:
            # Try to extract digits from the text
            digits = ''.join(filter(str.isdigit, text))
            if digits:
                return int(digits)
            return 0
    except Exception as e:
        logging.error(f"Error extracting number: {str(e)}")
        logging.error(traceback.format_exc())
        return 0