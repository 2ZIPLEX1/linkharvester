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
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
SYMPATHIES_PATH = os.path.join(TEMPLATES_PATH, 'sympathies')
LOG_FILE = os.path.join(PROJECT_PATH, 'image_recognition.log')

# Configure Tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

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
        
        # Save ROI for debugging if debug_name provided
        if debug_name:
            debug_dir = os.path.join(PROJECT_PATH, "debug_regions")
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"{debug_name}_roi.png")
            cv2.imwrite(debug_path, img_roi)
        
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
                
                # For debug visualization
                if debug_name:
                    debug_vis = img_roi.copy()
                    cv2.rectangle(debug_vis, 
                                 (max_loc[0], max_loc[1]),
                                 (max_loc[0] + w, max_loc[1] + h),
                                 (0, 255, 0), 2)
                    cv2.putText(debug_vis, f"{template_name} ({max_val:.2f})", 
                               (max_loc[0], max_loc[1] - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    debug_path = os.path.join(debug_dir, f"{debug_name}_detected.png")
                    cv2.imwrite(debug_path, debug_vis)
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
        
        # Save ROI for debugging if debug_name provided
        if debug_name:
            debug_dir = os.path.join(PROJECT_PATH, "debug_regions")
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"{debug_name}_number_roi.png")
            cv2.imwrite(debug_path, roi)
        
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to isolate the text
        _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
        
        # Save thresholded image for debugging
        if debug_name:
            thresh_path = os.path.join(debug_dir, f"{debug_name}_threshold.png")
            cv2.imwrite(thresh_path, thresh)
        
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