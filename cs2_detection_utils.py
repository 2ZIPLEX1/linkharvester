"""
CS2 Detection Utilities
Specialized functions for detecting various UI elements in CS2 screenshots.

This module contains all the computer vision and detection algorithms used
to analyze Counter-Strike 2 screenshots and identify buttons, medals, profile details, etc.
"""

import cv2
import os
import glob
import time
import logging
import numpy as np
import traceback

TESTING_MODE = False  # Set to False to disable testing mode

# Configure paths
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')

# Configure logging
LOG_FILE = os.path.join(PROJECT_PATH, 'image_recognition.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

def get_latest_screenshot(screenshot_path=None):
    """
    Get the most recent screenshot from Steam's screenshot folder or use provided path.
    Extracted from the original code to be reused across detection functions.
    """
    try:
        if screenshot_path:
            # Use the provided screenshot path
            if os.path.exists(screenshot_path):
                return screenshot_path
            else:
                logging.error(f"Provided screenshot does not exist: {screenshot_path}")
                return None
                
        # Default Steam screenshots path
        STEAM_SCREENSHOTS_PATH = r'C:\Program Files (x86)\Steam\userdata\1067368752\760\remote\730\screenshots'
        screenshots = glob.glob(os.path.join(STEAM_SCREENSHOTS_PATH, '*.jpg'))
        
        if not screenshots:
            logging.warning("No screenshots found")
            return None
            
        latest_screenshot = max(screenshots, key=os.path.getmtime)
        
        # Only use if it's less than 30 seconds old
        if time.time() - os.path.getmtime(latest_screenshot) > 30:
            logging.warning("No recent screenshots found")
            return None
            
        return latest_screenshot
    except Exception as e:
        logging.error(f"Error getting screenshot: {str(e)}")
        return None

def detect_template(image_input, template_name, threshold=None, roi=None):
    """
    Detect a template in an image.
    
    Args:
        image_input: Path to the screenshot image OR a numpy array of image data
        template_name: Name of the template to detect
        threshold: Matching threshold (0.0-1.0)
        roi: Region of interest (x, y, width, height) to restrict search
        
    Returns:
        tuple: (found, coordinates) where coordinates is (x, y) of the center of the match
    """
    try:
        # Set default thresholds for each template type
        default_thresholds = {
            "spectate_button": 0.8,
            "error_dialog": 0.7,
            "error_dialog_2": 0.7,
            "error_dialog_3": 0.7,
            "error_dialog_4": 0.7,
            "profile-button": 0.7,
            "right-arrow": 0.7
        }
        
        # Use provided threshold or default for this template
        if threshold is None:
            threshold = default_thresholds.get(template_name, 0.7)
        
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
            
            logging.info(f"Found {template_name} at coordinates: {center_x},{center_y} with confidence: {max_val:.3f}")
            return True, (center_x, center_y)
        else:
            return False, None
    except Exception as e:
        logging.error(f"Error detecting template {template_name}: {str(e)}")
        # Log traceback for easier debugging
        logging.error(traceback.format_exc())
        return False, None

#-----------------------------------------------------------------------------
# Profile Analysis Functions
#-----------------------------------------------------------------------------

def get_profile_roi(click_x, click_y, screenshot_path=None):
    """
    Extract the profile details region of interest from the screenshot.
    
    Args:
        click_x: X-coordinate of original click position
        click_y: Y-coordinate of original click position
        screenshot_path: Optional path to screenshot to use
        
    Returns:
        tuple: (profile_roi, roi_x, roi_y) or (None, None, None) on error
    """
    try:
        # Define the profile details ROI relative to click position
        roi_x = click_x + 28
        roi_y = click_y - 150
        roi_width = 384
        roi_height = 413
        
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot(screenshot_path)
        if not screenshot_path:
            logging.warning("No recent screenshot found for profile analysis")
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=No recent screenshot found")
            return None, None, None
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_ANALYSIS_ERROR=Could not read screenshot")
            return None, None, None
        
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
            return None, None, None
        
        # Extract the full profile details ROI
        profile_roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
        
        return profile_roi, roi_x, roi_y
        
    except Exception as e:
        logging.error(f"Error getting profile ROI: {str(e)}")
        logging.error(traceback.format_exc())
        print("PROFILE_ANALYSIS_RESULT=0")
        print(f"PROFILE_ANALYSIS_ERROR=Error getting profile ROI: {str(e)}")
        return None, None, None

def detect_profile_button_in_roi(profile_roi, roi_x, roi_y, visualization):
    """
    Detect the profile button in the profile ROI.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about the profile button detection
    """
    # Default result structure
    result = {
        "found": False,
        "x": 0,
        "y": 0,
        "confidence": 0.0
    }
    
    try:
        # Template matching for profile button icon
        template_path = os.path.join(TEMPLATES_PATH, "profile-button.jpg")
        
        if not os.path.exists(template_path):
            logging.warning(f"Profile button template not found at: {template_path}")
            return result
            
        template = cv2.imread(template_path)
        if template is None:
            logging.warning(f"Failed to load template image: {template_path}")
            return result
        
        # Convert to grayscale once
        full_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Try multiple methods and thresholds for detection
        detect_methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_SQDIFF_NORMED]
        thresholds = [0.7, 0.6, 0.5, 0.4]
        
        # Try each method and threshold for actual detection
        for method in detect_methods:
            if result["found"]:
                break
                
            for threshold in thresholds:
                if result["found"]:
                    break
                    
                # Perform template matching
                result_img = cv2.matchTemplate(full_gray, template_gray, method)
                
                # For SQDIFF methods, smaller values = better matches
                if method == cv2.TM_SQDIFF_NORMED:
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_img)
                    match_val = 1.0 - min_val  # Convert to a similarity score
                    match_loc = min_loc
                else:
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_img)
                    match_val = max_val
                    match_loc = max_loc
                
                if ((method == cv2.TM_SQDIFF_NORMED and match_val >= threshold) or 
                    (method != cv2.TM_SQDIFF_NORMED and match_val >= threshold)):
                    h, w = template.shape[:2]
                    # Calculate coordinates relative to full image
                    profile_button_x = roi_x + match_loc[0] + w//2
                    profile_button_y = roi_y + match_loc[1] + h//2
                    
                    result["found"] = True
                    result["x"] = profile_button_x
                    result["y"] = profile_button_y
                    result["confidence"] = match_val
                    
                    # Draw on visualization
                    cv2.rectangle(visualization, 
                                (match_loc[0], match_loc[1]),
                                (match_loc[0] + w, match_loc[1] + h),
                                (0, 255, 0), 2)
                    cv2.putText(visualization, f"Profile Button ({match_val:.2f})", 
                            (match_loc[0], match_loc[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    logging.info(f"Profile button found at {profile_button_x},{profile_button_y}")
                    break

        # If no profile button found with template matching, try color-based detection
        if not result["found"]:
            # Try color-based detection as fallback
            profile_button_result = detect_profile_button_by_color(profile_roi, roi_x, roi_y, visualization)
            
            if profile_button_result["found"]:
                # Copy all the fields
                result["found"] = True
                result["x"] = profile_button_result["x"]
                result["y"] = profile_button_result["y"]
                result["confidence"] = profile_button_result["confidence"]
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting profile button in ROI: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_profile_button_by_color(profile_roi, roi_x, roi_y, visualization):
    """
    Detect the profile button using color-based detection as a fallback.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about the profile button detection
    """
    # Default result structure
    result = {
        "found": False,
        "x": 0,
        "y": 0,
        "confidence": 0.5  # Default confidence for color detection
    }
    
    try:
        # Convert to HSV color space for better color filtering
        hsv = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2HSV)
        
        # Define range for white/light gray (common color for profile icons)
        lower_gray = np.array([0, 0, 180])
        upper_gray = np.array([180, 30, 255])
        
        # Threshold the HSV image to get only white/light areas
        mask = cv2.inRange(hsv, lower_gray, upper_gray)
        
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
        
        # If we found any potential buttons, use the largest one
        if filtered_contours:
            x, y, w, h, area = filtered_contours[0]
            
            result["found"] = True
            result["x"] = roi_x + x + w//2
            result["y"] = roi_y + y + h//2
            result["confidence"] = min(0.7, area / 500)  # Scale confidence by area, max 0.7
            
            # Draw on visualization
            cv2.rectangle(visualization, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(visualization, f"Profile Button (contour: {area:.1f})", 
                    (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            logging.info(f"Profile button found using contour method at {result['x']},{result['y']}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting profile button by color: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_medals_in_roi(profile_roi, roi_x, roi_y, visualization):
    """
    Detect medals in the profile ROI.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about medal detection
    """
    # Default result structure
    result = {
        "count": 0,
        "has_5year_coin": False,
        "detected_medals": []
    }
    
    try:
        # List of medal templates to check
        medal_templates = [
            "5-year-veteran-coin",
            "10-year-veteran-coin",
            "global-offensive-badge",
            "loyalty-badge",
            "premier-season-one-medal",
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
        
        # Convert profile ROI to grayscale once for all medal detections
        profile_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        
        # Process each medal template
        for template_name in medal_templates:
            # Define template path in the medals subfolder
            template_path = os.path.join(TEMPLATES_PATH, "medals", f"{template_name}.jpg")
            
            # Check if template file exists
            if not os.path.exists(template_path):
                continue
                
            # Read template
            template = cv2.imread(template_path)
            if template is None:
                continue
                
            # Convert to grayscale
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Check template size vs ROI size
            template_h, template_w = template_gray.shape
            if template_h > profile_gray.shape[0] or template_w > profile_gray.shape[1]:
                continue
            
            # Perform template matching with multiple thresholds
            thresholds = [0.85, 0.80, 0.75]
            medal_detected = False
            
            for threshold in thresholds:
                if medal_detected:
                    break
                    
                # Perform template matching
                result_img = cv2.matchTemplate(profile_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                
                # Find locations where match quality exceeds the threshold
                locations = np.where(result_img >= threshold)
                
                # If we have matches, process them
                if len(locations[0]) > 0:
                    # Group close matches using non-maximum suppression
                    rectangles = []
                    for pt in zip(*locations[::-1]):
                        rectangles.append((pt[0], pt[1], template_w, template_h))
                    
                    # Convert to numpy array for easier processing
                    if len(rectangles) > 0:
                        rectangles = np.array(rectangles)
                        
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
                                    
                                    if iou > 0.3:
                                        overlap = True
                                        break
                            
                            if not overlap:
                                picked_rectangles.append(rect)
                    
                        # Process the best match for this medal type
                        if picked_rectangles:
                            x, y, w, h = picked_rectangles[0]
                            confidence = float(result_img[y, x])
                            
                            # Only count each medal type once
                            if not medal_detected:
                                medal_detected = True
                                
                                # Add to the list of medal names if not already there
                                if template_name not in result["detected_medals"]:
                                    result["detected_medals"].append(template_name)
                                    result["count"] += 1  # Increment count only for new medals
                                
                                # Check if this is the 5-year veteran coin
                                if template_name == "5-year-veteran-coin":
                                    result["has_5year_coin"] = True
                            
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
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting medals in ROI: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_medal_arrow_in_roi(profile_roi, visualization):
    """
    Detect the medal arrow (more medals indicator) in the profile ROI.
    
    Args:
        profile_roi: The profile details region of interest
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about medal arrow detection
    """
    # Default result structure
    result = {
        "has_more_medals": False,
        "confidence": 0.0
    }
    
    try:
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Convert to grayscale once
        profile_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        
        # Load the arrow template
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
                        result["has_more_medals"] = True
                        result["confidence"] = max_val
                        
                        h, w = arrow_template.shape[:2]
                        
                        # Draw on visualization
                        cv2.rectangle(visualization, 
                                     (max_loc[0], max_loc[1]),
                                     (max_loc[0] + w, max_loc[1] + h),
                                     (0, 255, 0), 2)
                        cv2.putText(visualization, f"More Medals ({max_val:.2f})", 
                                   (max_loc[0], max_loc[1] - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        
                        # Save debug images
                        timestamp = int(time.time())
                        
                        # Save the full ROI with visualization
                        viz_path = os.path.join(debug_dir, f"medal_arrow_detection_{timestamp}.png")
                        cv2.imwrite(viz_path, visualization)
                        logging.info(f"Saved medal arrow visualization to {viz_path}")
                        
                        # Extract just the arrow region and save it
                        arrow_region = profile_roi[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
                        arrow_path = os.path.join(debug_dir, f"medal_arrow_found_{timestamp}_{max_val:.2f}.png")
                        cv2.imwrite(arrow_path, arrow_region)
                        logging.info(f"Saved detected arrow region to {arrow_path}")
                        
                        # Also save the template for comparison
                        template_path = os.path.join(debug_dir, f"medal_arrow_template_{timestamp}.png")
                        cv2.imwrite(template_path, arrow_template)
                        
                        logging.info("More medals arrow detected and saved to debug regions")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting medal arrow in ROI: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def make_medal_decision(medal_count, has_5year_coin, has_more_medals):
    """
    Make a decision based on medal criteria.
    
    Args:
        medal_count: Number of medals detected
        has_5year_coin: Whether the 5-year veteran coin was detected
        has_more_medals: Whether the more medals indicator was detected
        
    Returns:
        dict: Decision information
    """
    # Default result structure
    result = {
        "meets_criteria": False,
        "reason": ""
    }
    
    # Log the original input values before any modifications
    logging.info(f"Medal decision input: count={medal_count}, 5yr={has_5year_coin}, more={has_more_medals}")
    
    # If more medals indicator is found, add it to the count to represent hidden medals
    # This helps account for medals that might be out of view
    adjusted_medal_count = medal_count
    if has_more_medals:
        adjusted_medal_count += 2  # Assume at least 2 more medals if arrow is present
        logging.info(f"More medals indicator detected, adjusting count from {medal_count} to {adjusted_medal_count}")
    
    # Apply testing mode ONLY if we have at least 3 medals
    has_sufficient_medals = adjusted_medal_count >= 3
    
    original_criteria_met = has_5year_coin and has_sufficient_medals
    testing_mode_applied = False
    
    if TESTING_MODE and has_sufficient_medals:
        original_5year_status = has_5year_coin
        has_5year_coin = True
        testing_mode_applied = True
        logging.warning(f"TESTING MODE: Found {adjusted_medal_count} medals, 5-year veteran coin detection changed from {original_5year_status} to TRUE")
    
    # Decision criteria:
    # 1. Has 5-year veteran coin
    # 2. Has at least 3 medals total (including adjustment for more medals indicator)
    meets_criteria = has_5year_coin and has_sufficient_medals
    
    if meets_criteria:
        result["meets_criteria"] = True
        
        if testing_mode_applied:
            result["reason"] = f"Player has 5-year coin (FORCED TRUE by TESTING MODE) and {adjusted_medal_count} medals"
            if has_more_medals:
                result["reason"] += f" (including {adjusted_medal_count - medal_count} estimated from more-medals indicator)"
        else:
            result["reason"] = f"Player has 5-year coin and {adjusted_medal_count} medals"
            if has_more_medals:
                result["reason"] += f" (including {adjusted_medal_count - medal_count} estimated from more-medals indicator)"
    else:
        if not has_5year_coin:
            result["reason"] = "Missing 5-year veteran coin"
            if testing_mode_applied:
                result["reason"] += " (would have been forced TRUE in TESTING MODE but original criteria not met)"
        elif not has_sufficient_medals:
            result["reason"] = f"Insufficient medals ({adjusted_medal_count}/3 required)"
            if has_more_medals:
                result["reason"] += f" (includes {adjusted_medal_count - medal_count} estimated from more-medals indicator)"
        else:
            result["reason"] = "Unknown reason for not meeting criteria"
    
    # Add whether testing mode was applied to the result
    result["testing_mode_applied"] = testing_mode_applied
    result["original_criteria_met"] = original_criteria_met
    
    # Log detailed decision information
    logging.info(f"Medal decision: {result['meets_criteria']} - {result['reason']}")
    if testing_mode_applied:
        logging.info(f"Testing mode was applied. Original criteria met: {original_criteria_met}")
    
    return result