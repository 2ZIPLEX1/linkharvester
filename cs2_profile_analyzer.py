"""
CS2 Profile Analyzer - Refactored
Specialized module for analyzing player profiles in Counter-Strike 2.

This module uses the detection utilities to analyze player profiles, check medals,
and make decisions on whether to proceed with viewing a player's Steam profile.
"""

import os
import time
import logging
import cv2
import traceback
import numpy as np
import glob

from detect_sympathies import detect_sympathy_template, extract_sympathy_number

# Configure logging
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
MEDALS_PATH = os.path.join(TEMPLATES_PATH, 'medals')
UNWANTED_MEDALS_PATH = os.path.join(MEDALS_PATH, 'unwanted')
LOG_FILE = os.path.join(PROJECT_PATH, 'profile_analyzer.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

def get_latest_screenshot(screenshot_path=None):
    """
    Get the most recent screenshot from Steam's screenshot folder or use provided path.
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
            return None, None, None
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
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
            return None, None, None
        
        # Extract the full profile details ROI
        profile_roi = img[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width]
        
        return profile_roi, roi_x, roi_y
        
    except Exception as e:
        logging.error(f"Error getting profile ROI: {str(e)}")
        logging.error(traceback.format_exc())
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
        
        # Try multiple methods and thresholds for detection (restored to original implementation)
        detect_methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_SQDIFF_NORMED]
        thresholds = [0.95, 0.9]
        
        # Try each method and threshold for actual detection
        for method in detect_methods:
            if result["found"]:
                break
                
            for threshold in thresholds:
                if result["found"]:
                    break
                    
                # Perform template matching
                result_img = cv2.matchTemplate(full_gray, template_gray, method)
                
                # For SQDIFF methods, smaller values = better matches (restored special handling)
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
                    
                    logging.info(f"Profile button found at {profile_button_x},{profile_button_y} with method {method} and confidence {match_val:.2f}")
                    break

        # If no profile button found with template matching, try color-based detection
        if not result["found"]:
            # Try color-based detection as fallback
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
                # More strict size filtering to reduce false positives
                if 80 < area < 400:  # Narrowed range from original 50-500
                    x, y, w, h = cv2.boundingRect(contour)
                    # Stricter aspect ratio filter for profile icons
                    aspect_ratio = float(w) / h
                    if 0.8 < aspect_ratio < 1.2:  # Narrowed from original 0.7-1.3
                        filtered_contours.append((x, y, w, h, area))
            
            # Sort by area (largest first)
            filtered_contours.sort(key=lambda x: x[4], reverse=True)
            
            # If we found any potential buttons, use the largest one
            if filtered_contours and len(filtered_contours) <= 3:  # Limit to max 3 candidates to reduce false positives
                x, y, w, h, area = filtered_contours[0]
                
                # Lower confidence and stricter conditions for color-based detection
                confidence = min(0.6, area / 500)  # Reduced from 0.7 to 0.6
                
                # Only consider found if confidence is sufficient
                if confidence >= 0.45:  # Added minimum threshold
                    result["found"] = True
                    result["x"] = roi_x + x + w//2
                    result["y"] = roi_y + y + h//2
                    result["confidence"] = confidence
                    
                    # Draw on visualization
                    cv2.rectangle(visualization, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(visualization, f"Profile Button (contour: {area:.1f}, conf: {confidence:.2f})", 
                            (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    logging.info(f"Profile button found using contour method at {result['x']},{result['y']} with confidence {confidence:.2f}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting profile button in ROI: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_sympathies_in_roi(profile_roi, roi_x, roi_y, visualization):
    """
    Detect sympathies (smile, teach, crown) icons and their values in the profile ROI.
    Uses a common search region to handle cases where fewer than 3 icons are present.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about sympathies detection
    """
    # Default result structure
    result = {
        "smile_value": 0,
        "teach_value": 0,
        "crown_value": 0,
        "sympathies_sum": 0,
        "too_many_sympathies": False
    }
    
    try:
        # Create timestamp for debug images
        timestamp = int(time.time())
        
        # Define a common search region for all icons
        # The sympathies region starts ~125px from the click position
        # and spans about 150px width to cover all possible icons
        sympathies_x = 38 + 55  # 38px to adjust for ROI, then 125px offset from click
        sympathies_y = 140       # Approximate Y position (may vary)
        sympathies_width = 220   # Increased width to capture all icons and numbers (increased from 200)
        sympathies_height = 105   # Height to capture vertical variation
        
        # Create a single ROI for all sympathies
        sympathies_region = profile_roi[sympathies_y:sympathies_y+sympathies_height, 
                                        sympathies_x:sympathies_x+sympathies_width]
        
        # Define the icon templates to search for
        icon_configs = [
            {"name": "smile", "width": 25, "height": 25, "min_spacing": 50},
            {"name": "teach", "width": 25, "height": 24, "min_spacing": 50},
            {"name": "crown", "width": 26, "height": 26, "min_spacing": 50}
        ]
        
        # Detected icon positions (to handle potential overlaps)
        detected_positions = []
        
        # Process each icon type within the common region
        for config in icon_configs:
            icon_name = config["name"]
            icon_width = config["width"]
            icon_height = config["height"]
            min_spacing = config["min_spacing"]
            
            # REMOVED: Debug name for this icon
            # Pass None instead of a debug name to prevent saving individual icon images
            
            # Detect the icon within the sympathies region
            found, coords, confidence = detect_sympathy_template(
                sympathies_region, icon_name, threshold=0.7, debug_name=None)
            
            if found:
                # Check if this detection overlaps with previous ones
                is_duplicate = False
                for pos in detected_positions:
                    # Calculate distance to previous detections
                    dist_x = abs(coords[0] - pos[0])
                    if dist_x < min_spacing:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    # Store the position to check for duplicates
                    detected_positions.append(coords)
                    
                    # Extract the exact coordinates relative to the sympathies region
                    icon_x = coords[0] - icon_width // 2
                    icon_y = coords[1] - icon_height // 2
                    
                    # Draw rectangle around found icon on the visualization (adjust to full ROI coords)
                    cv2.rectangle(visualization, 
                                 (sympathies_x + icon_x, sympathies_y + icon_y),
                                 (sympathies_x + icon_x + icon_width, sympathies_y + icon_y + icon_height),
                                 (0, 255, 0), 2)
                    cv2.putText(visualization, f"{icon_name} ({confidence:.2f})", 
                              (sympathies_x + icon_x, sympathies_y + icon_y - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    # Define number ROI to the right of the icon
                    number_width = 37  # Width to capture number
                    number_height = icon_height
                    
                    # Coordinates relative to the sympathies region
                    number_x = icon_x + icon_width
                    number_y = icon_y
                    
                    # Check if number region is within bounds
                    if number_x + number_width <= sympathies_width:
                        # Extract the number using the utility function
                        # Pass None instead of debug_name to prevent saving number region images
                        number_value = extract_sympathy_number(
                            sympathies_region, 
                            number_x, 
                            number_y, 
                            number_width, 
                            number_height, 
                            debug_name=None
                        )
                        
                        # Store the value
                        result[f"{icon_name}_value"] = number_value
                        
                        # Draw number area and value on visualization
                        cv2.rectangle(visualization, 
                                     (sympathies_x + number_x, sympathies_y + number_y),
                                     (sympathies_x + number_x + number_width, sympathies_y + number_y + number_height),
                                     (255, 0, 0), 1)
                        
                        cv2.putText(visualization, f"{number_value}", 
                                   (sympathies_x + number_x, sympathies_y + number_y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        
                        logging.info(f"Detected {icon_name} with value {number_value}")
                    else:
                        logging.warning(f"Number region for {icon_name} would be out of bounds")
                else:
                    logging.info(f"Skipping {icon_name} detection as it overlaps with another icon")
            else:
                logging.info(f"Could not detect {icon_name} icon (confidence: {confidence:.2f})")
        
        # Calculate the sum
        result["sympathies_sum"] = (result["smile_value"] + 
                                   result["teach_value"] + 
                                   result["crown_value"])
        
        # Determine if there are too many sympathies
        result["too_many_sympathies"] = result["sympathies_sum"] > 100
        
        # Add sum to visualization
        cv2.putText(visualization, f"Sympathies Sum: {result['sympathies_sum']}", 
                   (10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        logging.info(f"Sympathies detection complete: smile={result['smile_value']}, " +
                    f"teach={result['teach_value']}, crown={result['crown_value']}, " +
                    f"sum={result['sympathies_sum']}, too_many={result['too_many_sympathies']}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting sympathies in ROI: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_unwanted_medals(profile_roi, roi_x, roi_y, visualization):
    """
    Check for unwanted medals in the profile ROI.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about unwanted medal detection
    """
    # Default result structure
    result = {
        "unwanted_medals_found": False,
        "detected_unwanted_medals": []
    }
    
    try:
        # Get all unwanted medal templates from the unwanted medals folder
        unwanted_medal_files = []
        for ext in ['jpg', 'png']:
            unwanted_medal_files.extend(glob.glob(os.path.join(UNWANTED_MEDALS_PATH, f"*.{ext}")))
        
        if not unwanted_medal_files:
            logging.warning("No unwanted medal templates found")
            return result
            
        # Convert profile ROI to grayscale once for all medal detections
        profile_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        
        # Process each unwanted medal template
        for template_path in unwanted_medal_files:
            medal_name = os.path.splitext(os.path.basename(template_path))[0]
            
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
            thresholds = [0.9, 0.85]
            
            for threshold in thresholds:
                # Perform template matching
                result_img = cv2.matchTemplate(profile_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_img)
                
                if max_val >= threshold:
                    # We found an unwanted medal
                    result["unwanted_medals_found"] = True
                    result["detected_unwanted_medals"].append(medal_name)
                    
                    h, w = template.shape[:2]
                    
                    # Draw on visualization
                    cv2.rectangle(visualization, 
                                 (max_loc[0], max_loc[1]),
                                 (max_loc[0] + w, max_loc[1] + h),
                                 (0, 0, 255), 2)  # Red for unwanted medals
                    cv2.putText(visualization, f"UNWANTED: {medal_name} ({max_val:.2f})", 
                               (max_loc[0], max_loc[1] - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                    
                    logging.info(f"Unwanted medal detected: {medal_name} with confidence {max_val:.2f}")
                    
                    # Early exit - no need to check more medals if we already found an unwanted one
                    return result
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting unwanted medals: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_regular_medals(profile_roi, roi_x, roi_y, visualization):
    """
    Detect regular medals in the profile ROI.
    
    Args:
        profile_roi: The profile details region of interest
        roi_x: X-coordinate of the ROI in the original image
        roi_y: Y-coordinate of the ROI in the original image
        visualization: Image to draw detection results on
        
    Returns:
        dict: Information about regular medal detection
    """
    # Default result structure
    result = {
        "count": 0,
        "has_5year_coin": False,
        "detected_medals": []
    }
    
    try:
        # Get all regular medal templates from the medals folder (excluding unwanted subfolder)
        regular_medal_files = []
        
        # Get all files directly in the medals folder
        for ext in ['jpg', 'png']:
            medal_files = glob.glob(os.path.join(MEDALS_PATH, f"*.{ext}"))
            regular_medal_files.extend(medal_files)
        
        if not regular_medal_files:
            logging.warning("No regular medal templates found")
            return result
            
        # Convert profile ROI to grayscale once for all medal detections
        profile_gray = cv2.cvtColor(profile_roi, cv2.COLOR_BGR2GRAY)
        
        # Process each regular medal template
        for template_path in regular_medal_files:
            medal_name = os.path.splitext(os.path.basename(template_path))[0]
            
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
            thresholds = [0.9, 0.85]
            medal_detected = False
            
            for threshold in thresholds:
                if medal_detected:
                    break
                    
                # Perform template matching
                result_img = cv2.matchTemplate(profile_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_img)
                
                if max_val >= threshold:
                    # We found a regular medal
                    medal_detected = True
                    
                    # Add to the list of medal names if not already there
                    if medal_name not in result["detected_medals"]:
                        result["detected_medals"].append(medal_name)
                        result["count"] += 1  # Increment count only for new medals
                    
                    # Check if this is the 5-year veteran coin
                    if medal_name == "5-year-veteran-coin":
                        result["has_5year_coin"] = True
                        logging.info("5-year veteran coin detected")
                    
                    h, w = template.shape[:2]
                    
                    # Draw on visualization
                    cv2.rectangle(visualization, 
                                 (max_loc[0], max_loc[1]),
                                 (max_loc[0] + w, max_loc[1] + h),
                                 (0, 255, 0), 2)  # Green for regular medals
                    cv2.putText(visualization, f"{medal_name} ({max_val:.2f})", 
                               (max_loc[0], max_loc[1] - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    logging.info(f"Regular medal detected: {medal_name} with confidence {max_val:.2f}")
                    
                    # Break after finding this medal and move to the next one
                    break
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting regular medals: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def detect_medal_arrow(click_x, click_y, screenshot_path=None, visualization=None):
    """
    Detect the medal arrow using precise offset from the original click position.
    
    Args:
        click_x: X-coordinate of original click position
        click_y: Y-coordinate of original click position
        screenshot_path: Optional path to screenshot to use
        visualization: Optional visualization image
        
    Returns:
        dict: Information about medal arrow detection
    """
    # Default result structure
    result = {
        "has_more_medals": False,
        "confidence": 0.0,
        "is_active": False,
        "arrow_x": 0,
        "arrow_y": 0
    }
    
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot(screenshot_path)
        if not screenshot_path:
            logging.warning("No recent screenshot found for arrow detection")
            return result
        
        # Read the screenshot
        img = cv2.imread(screenshot_path)
        if img is None:
            logging.error(f"Could not read image: {screenshot_path}")
            return result
        
        # Define precise arrow region using exact measurements
        # Arrow is 390px from click X, in the top 140px of profile ROI
        arrow_x = click_x + 390
        
        # Calculate potential Y positions - arrow could be in top 140px of profile ROI
        # Profile ROI starts at click_y - 150, so arrow is between click_y - 150 and click_y - 10
        arrow_min_y = click_y - 150  # Top of profile ROI
        arrow_max_y = click_y - 10   # 140px from top of profile ROI
        
        # Get image dimensions
        img_height, img_width = img.shape[:2]
        
        # Ensure coordinates are within image bounds
        if arrow_x >= img_width or arrow_min_y < 0 or arrow_max_y >= img_height:
            logging.error(f"Arrow region out of bounds: x={arrow_x}, y_min={arrow_min_y}, y_max={arrow_max_y}")
            return result
        
        # Load the arrow template
        arrow_template_path = os.path.join(TEMPLATES_PATH, "right-arrow.jpg")
        if not os.path.exists(arrow_template_path):
            logging.error(f"Arrow template not found: {arrow_template_path}")
            return result
            
        arrow_template = cv2.imread(arrow_template_path)
        if arrow_template is None:
            logging.error(f"Could not read arrow template: {arrow_template_path}")
            return result
            
        arrow_template_gray = cv2.cvtColor(arrow_template, cv2.COLOR_BGR2GRAY)
        
        # Extract and check the region where arrow should be
        arrow_region_height = arrow_max_y - arrow_min_y
        arrow_region = img[arrow_min_y:arrow_max_y, arrow_x:arrow_x+20]  # 20px width to account for template width
        
        if arrow_region.size == 0:
            logging.error("Arrow region has zero size")
            return result
            
        arrow_region_gray = cv2.cvtColor(arrow_region, cv2.COLOR_BGR2GRAY)
        
        # Perform template matching
        result_img = cv2.matchTemplate(arrow_region_gray, arrow_template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_img)
        
        logging.info(f"Medal arrow match confidence in precise region: {max_val:.3f}")
        
        # Check if we found a match based on confidence threshold
        # Use a lower threshold (0.5) to detect both active and inactive arrows
        if max_val >= 0.5:
            h, w = arrow_template.shape[:2]
            
            # Extract the matched region
            matched_region = arrow_region[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
            
            # Analyze brightness to determine if arrow is active or inactive
            is_active = analyze_arrow_activity(matched_region)
            
            # Only consider it a "more medals" indicator if it's an active arrow
            # with higher confidence (0.7+)
            if is_active and max_val >= 0.7:
                result["has_more_medals"] = True
                result["is_active"] = True
            else:
                # Either inactive or low confidence match
                result["has_more_medals"] = False
                result["is_active"] = is_active
                
            result["confidence"] = max_val
            
            # Calculate absolute Y position in the original image
            absolute_y = arrow_min_y + max_loc[1]
            
            # Store the absolute coordinates
            result["arrow_x"] = arrow_x + max_loc[0]
            result["arrow_y"] = absolute_y
            
            # Draw on visualization if provided
            if visualization is not None:
                # Use green for active arrows, red for inactive
                color = (0, 255, 0) if is_active else (0, 0, 255)
                
                cv2.rectangle(visualization, 
                             (max_loc[0], max_loc[1]),
                             (max_loc[0] + w, max_loc[1] + h),
                             color, 2)
                cv2.putText(visualization, 
                           f"{'Active' if is_active else 'Inactive'} Arrow ({max_val:.2f})", 
                           (max_loc[0], max_loc[1] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Log detection results
            status = "active" if is_active else "inactive"
            logging.info(f"Medal arrow detected ({status}) with confidence {max_val:.2f} at position {result['arrow_x']},{result['arrow_y']}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting medal arrow: {str(e)}")
        logging.error(traceback.format_exc())
        return result

def analyze_arrow_activity(arrow_region):
    """
    Analyze the brightness/contrast of the arrow region to determine if it's active or inactive.
    
    Args:
        arrow_region: The extracted region where the arrow was detected
        
    Returns:
        bool: True if the arrow appears to be active, False if inactive
    """
    try:
        # Convert to grayscale if it's not already
        if len(arrow_region.shape) > 2:
            gray_arrow = cv2.cvtColor(arrow_region, cv2.COLOR_BGR2GRAY)
        else:
            gray_arrow = arrow_region
            
        # Calculate brightness metrics
        mean_brightness = np.mean(gray_arrow)
        std_dev = np.std(gray_arrow)
        
        # Calculate contrast (using standard deviation as a proxy for contrast)
        contrast = std_dev
        
        logging.info(f"Arrow brightness analysis: mean={mean_brightness:.1f}, contrast={contrast:.1f}")
        
        # Thresholds for active arrows - these may need adjustment based on your game's visuals
        brightness_threshold = 125
        contrast_threshold = 25
        
        # If we have very high contrast (>90), consider it active regardless of brightness
        high_contrast_override = contrast > 90
        
        is_active = high_contrast_override or ((mean_brightness >= brightness_threshold) and (contrast >= contrast_threshold))
        
        return is_active
        
    except Exception as e:
        logging.error(f"Error analyzing arrow activity: {str(e)}")
        # Default to considering it active if analysis fails (safer to check than to skip)
        return True

def analyze_profile(click_x, click_y, screenshot_path=None):
    """
    Unified profile analysis function that follows the desired algorithm flow.
    
    Args:
        click_x: X-coordinate of original click position on player in scoreboard
        click_y: Y-coordinate of original click position on player in scoreboard
        screenshot_path: Optional path to screenshot to use
        
    Returns:
        Outputs structured flags through print statements for AHK
    """
    try:
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Default result structure
        result = {
            "profile_button_found": False,
            "profile_button_x": 0,
            "profile_button_y": 0,
            "unwanted_medals_found": False,
            "medal_count": 0,
            "five_year_medal_found": False,
            "more_medals_available": False,
            "arrow_x": 0,
            "arrow_y": 0
        }
        
        # STEP 1: Get the profile ROI from the screenshot
        profile_roi, roi_x, roi_y = get_profile_roi(click_x, click_y, screenshot_path)
        
        # Get the full screenshot for attention icon detection
        screenshot_path = get_latest_screenshot(screenshot_path)
        if screenshot_path:
            full_img = cv2.imread(screenshot_path)
            
            # Look for the next attention icon
            from cs2_detect import find_attention_icon_in_region
            icon_found, icon_coords, next_click_coords = find_attention_icon_in_region(
                full_img, click_y)
                
            if icon_found:
                print(f"NEXT_ATTENTION_ICON_FOUND=1")
                print(f"NEXT_ATTENTION_ICON_COORDS={icon_coords[0]},{icon_coords[1]}")
                print(f"NEXT_CLICK_COORDS={next_click_coords[0]},{next_click_coords[1]}")
                logging.info(f"Found next attention icon at {icon_coords}, suggesting next click at {next_click_coords}")
            else:
                print("NEXT_ATTENTION_ICON_FOUND=0")
                logging.info("No next attention icon found")
        
        if profile_roi is None:
            # Error already logged and printed by get_profile_roi
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_BUTTON_FOUND=0")
            print("SYMPATHIES_SUM=0")
            print("SMILE_VALUE=0")
            print("TEACH_VALUE=0")
            print("CROWN_VALUE=0")
            print("TOO_MANY_SYMPATHIES=0")
            print("UNWANTED_MEDALS_FOUND=0")
            print("THREE_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            return
            
        # Create a visualization image for our detections
        visualization = profile_roi.copy()
        
        # Save timestamp for debug images
        timestamp = int(time.time())
        
        # STEP 2: Detect profile button
        profile_button_result = detect_profile_button_in_roi(profile_roi, roi_x, roi_y, visualization)
        result["profile_button_found"] = profile_button_result["found"]
        
        # If no profile button found, exit early with structured output
        if not result["profile_button_found"]:
            logging.info("No profile button detected in profile details")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=0")
            print("TOO_MANY_SYMPATHIES=0")
            print("UNWANTED_MEDALS_FOUND=0")
            print("THREE_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            print("SYMPATHIES_SUM=0")
            print("TOO_MANY_SYMPATHIES=0")
            
            return
            
        # Store profile button coordinates
        result["profile_button_x"] = profile_button_result["x"]
        result["profile_button_y"] = profile_button_result["y"]
        
        # STEP 3: Check for sympathies now that we know the profile button exists
        sympathies_result = detect_sympathies_in_roi(profile_roi, roi_x, roi_y, visualization)
        
        # If too many sympathies, exit early
        if sympathies_result["too_many_sympathies"]:
            logging.info(f"Too many sympathies detected: {sympathies_result['sympathies_sum']} > 100")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=1")
            print(f"PROFILE_BUTTON_COORDS={result['profile_button_x']},{result['profile_button_y']}")
            print(f"SYMPATHIES_SUM={sympathies_result['sympathies_sum']}")
            print(f"SMILE_VALUE={sympathies_result['smile_value']}")
            print(f"TEACH_VALUE={sympathies_result['teach_value']}")
            print(f"CROWN_VALUE={sympathies_result['crown_value']}")
            print("TOO_MANY_SYMPATHIES=1")
            print("UNWANTED_MEDALS_FOUND=0")  # Not relevant when skipping due to sympathies
            print("THREE_PLUS_MEDALS_FOUND=0") # Not relevant when skipping due to sympathies
            print("FIVE_YEAR_MEDAL_FOUND=0")  # Not relevant when skipping due to sympathies
            print("CLICK_TO_SEE_MORE_MEDALS=0")  # Not relevant when skipping due to sympathies
            
            return
        
        # STEP 4: Check for unwanted medals first
        unwanted_medal_result = detect_unwanted_medals(profile_roi, roi_x, roi_y, visualization)
        result["unwanted_medals_found"] = unwanted_medal_result["unwanted_medals_found"]
        
        # If unwanted medals found, exit early
        if result["unwanted_medals_found"]:
            logging.info("Unwanted medals detected, stopping analysis")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=1")
            print(f"PROFILE_BUTTON_COORDS={result['profile_button_x']},{result['profile_button_y']}")
            print(f"SYMPATHIES_SUM={sympathies_result['sympathies_sum']}")
            print(f"SMILE_VALUE={sympathies_result['smile_value']}")
            print(f"TEACH_VALUE={sympathies_result['teach_value']}")
            print(f"CROWN_VALUE={sympathies_result['crown_value']}")
            print("TOO_MANY_SYMPATHIES=0")
            print("UNWANTED_MEDALS_FOUND=1")
            print("THREE_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            
            # Add detected unwanted medals to output
            for medal_name in unwanted_medal_result["detected_unwanted_medals"]:
                print(f"UNWANTED_MEDAL_DETECTED={medal_name}")

            return
        
        # STEP 5: Detect regular medals
        medal_result = detect_regular_medals(profile_roi, roi_x, roi_y, visualization)
        result["medal_count"] = medal_result["count"]
        result["five_year_medal_found"] = medal_result["has_5year_coin"]
        
        # Check if we have fewer than 3 medals
        has_three_plus_medals = result["medal_count"] >= 3
        if not has_three_plus_medals:
            logging.info(f"Insufficient medals detected: {result['medal_count']}/4 required")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=1")
            print(f"PROFILE_BUTTON_COORDS={result['profile_button_x']},{result['profile_button_y']}")
            print(f"SYMPATHIES_SUM={sympathies_result['sympathies_sum']}")
            print(f"SMILE_VALUE={sympathies_result['smile_value']}")
            print(f"TEACH_VALUE={sympathies_result['teach_value']}")
            print(f"CROWN_VALUE={sympathies_result['crown_value']}")
            print("TOO_MANY_SYMPATHIES=0")
            print("UNWANTED_MEDALS_FOUND=0")
            print("THREE_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            print(f"MEDAL_COUNT={result['medal_count']}")
            
            # Include individual medal information
            for medal_name in medal_result["detected_medals"]:
                print(f"MEDAL_DETECTED={medal_name}")

            return
        
        # STEP 6: Check for medal arrow
        arrow_result = detect_medal_arrow(click_x, click_y, screenshot_path, visualization)
        result["more_medals_available"] = arrow_result["has_more_medals"]
        result["arrow_x"] = arrow_result["arrow_x"]
        result["arrow_y"] = arrow_result["arrow_y"]
        
        # STEP 6: Output final results
        print("PROFILE_ANALYSIS_RESULT=1")
        print("PROFILE_BUTTON_FOUND=1")
        print(f"PROFILE_BUTTON_COORDS={result['profile_button_x']},{result['profile_button_y']}")
        print(f"SYMPATHIES_SUM={sympathies_result['sympathies_sum']}")
        print(f"SMILE_VALUE={sympathies_result['smile_value']}")
        print(f"TEACH_VALUE={sympathies_result['teach_value']}")
        print(f"CROWN_VALUE={sympathies_result['crown_value']}")
        print("TOO_MANY_SYMPATHIES=0")
        print("UNWANTED_MEDALS_FOUND=0")
        print(f"THREE_PLUS_MEDALS_FOUND={1 if has_three_plus_medals else 0}")
        print(f"FIVE_YEAR_MEDAL_FOUND={1 if result['five_year_medal_found'] else 0}")
        print(f"CLICK_TO_SEE_MORE_MEDALS={1 if result['more_medals_available'] else 0}")
        
        # Include arrow coordinates if an arrow was detected
        if result["more_medals_available"]:
            print(f"ARROW_COORDS_X={result['arrow_x']}")
            print(f"ARROW_COORDS_Y={result['arrow_y']}")
            print(f"ARROW_COORDS={result['arrow_x']},{result['arrow_y']}")
        
        # Include medal count information
        print(f"MEDAL_COUNT={result['medal_count']}")
        
        # Include individual medal information
        for medal_name in medal_result["detected_medals"]:
            print(f"MEDAL_DETECTED={medal_name}")
        
        # Save debug visualization with all detections
        debug_path = os.path.join(debug_dir, f"profile_complete_analysis_{timestamp}.png")
        cv2.imwrite(debug_path, visualization)
        
        logging.info(f"Profile analysis complete: {result['medal_count']} medals, " +
                     f"5-year coin: {result['five_year_medal_found']}, " +
                     f"More medals available: {result['more_medals_available']}")
        
    except Exception as e:
        logging.error(f"Error in profile analysis: {str(e)}")
        logging.error(traceback.format_exc())
        print("PROFILE_ANALYSIS_RESULT=0")
        print("PROFILE_BUTTON_FOUND=0")
        print("SYMPATHIES_SUM=0")
        print("SMILE_VALUE=0")
        print("TEACH_VALUE=0")
        print("CROWN_VALUE=0")
        print("TOO_MANY_SYMPATHIES=0")
        print("UNWANTED_MEDALS_FOUND=0")
        print("THREE_PLUS_MEDALS_FOUND=0")
        print("FIVE_YEAR_MEDAL_FOUND=0")
        print("CLICK_TO_SEE_MORE_MEDALS=0")
        print(f"PROFILE_ANALYSIS_ERROR={str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        try:
            click_x = int(sys.argv[1])
            click_y = int(sys.argv[2])
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