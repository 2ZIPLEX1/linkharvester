"""
CS2 Profile Analyzer
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
from cs2_detection_utils import get_latest_screenshot

# Import detection utilities
from cs2_detection_utils import (
    get_profile_roi, 
    detect_profile_button_in_roi,
    detect_medals_in_roi,
    detect_medal_arrow_in_roi,
    make_medal_decision
)

# Configure logging
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'recognition', 'templates')
LOG_FILE = os.path.join(PROJECT_PATH, 'profile_analyzer.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

def analyze_profile(click_x, click_y, screenshot_path=None):
    """
    Unified profile analysis function that outputs structured flags for decision making.
    
    Args:
        click_x: X-coordinate of original click position on player in scoreboard
        click_y: Y-coordinate of original click position on player in scoreboard
        screenshot_path: Optional path to screenshot to use
        
    Returns:
        Outputs structured flags through print statements
    """
    try:
        # Get the profile ROI from the screenshot
        profile_roi, roi_x, roi_y = get_profile_roi(click_x, click_y, screenshot_path)
        if profile_roi is None:
            # Error already logged and printed by get_profile_roi
            print("PROFILE_ANALYSIS_RESULT=0")
            print("PROFILE_BUTTON_FOUND=0")
            print("FOUR_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("UNWANTED_MEDALS_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            return
            
        # Create a visualization image for our detections
        visualization = profile_roi.copy()
        
        # Detect profile button
        profile_button_result = detect_profile_button_in_roi(profile_roi, roi_x, roi_y, visualization)
        profile_button_found = profile_button_result["found"]
        
        # If no profile button found, exit early with structured output
        if not profile_button_found:
            logging.info("No profile button detected in profile details")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=0")
            print("FOUR_PLUS_MEDALS_FOUND=0")
            print("FIVE_YEAR_MEDAL_FOUND=0")
            print("UNWANTED_MEDALS_FOUND=0")
            print("CLICK_TO_SEE_MORE_MEDALS=0")
            return
            
        # Log and print profile button coordinates
        profile_button_x = profile_button_result["x"]
        profile_button_y = profile_button_result["y"]
        print("PROFILE_BUTTON_FOUND=1")
        print(f"PROFILE_BUTTON_COORDS={profile_button_x},{profile_button_y}")
        
        # Detect medals
        medal_result = detect_medals_in_roi(profile_roi, roi_x, roi_y, visualization)
        
        # Check for medal arrow using precise offset from original click
        arrow_result = detect_precise_medal_arrow(click_x, click_y, screenshot_path, visualization)
        
        # Check for unwanted medals (like hydra pin and aces high pin)
        unwanted_medals_found = check_for_unwanted_medals(medal_result["detected_medals"])
        
        # Determine if we have 4+ medals
        four_plus_medals = medal_result["count"] >= 4
        
        # Check for 5-year medal specifically
        five_year_medal_found = medal_result["has_5year_coin"]
        
        # Output results in the new structured format
        print("PROFILE_ANALYSIS_RESULT=1")
        print(f"PROFILE_BUTTON_FOUND={1 if profile_button_found else 0}")
        print(f"FOUR_PLUS_MEDALS_FOUND={1 if four_plus_medals else 0}")
        print(f"FIVE_YEAR_MEDAL_FOUND={1 if five_year_medal_found else 0}")
        print(f"UNWANTED_MEDALS_FOUND={1 if unwanted_medals_found else 0}")
        print(f"CLICK_TO_SEE_MORE_MEDALS={1 if arrow_result['has_more_medals'] else 0}")
        
        # Include arrow coordinates if an arrow was detected
        if arrow_result["has_more_medals"] and "arrow_x" in arrow_result and "arrow_y" in arrow_result:
            arrow_x = arrow_result["arrow_x"]
            arrow_y = arrow_result["arrow_y"]
            print(f"ARROW_COORDS_X={arrow_x}")
            print(f"ARROW_COORDS_Y={arrow_y}")
            print(f"ARROW_COORDS={arrow_x},{arrow_y}")
        
        # Include medal count information
        print(f"MEDAL_COUNT={medal_result['count']}")
        
        # Include individual medal information
        for medal_name in medal_result["detected_medals"]:
            print(f"MEDAL_DETECTED={medal_name}")
        
        logging.info(f"Profile analysis complete: {medal_result['count']} medals, " +
                    f"5-year coin: {five_year_medal_found}, " +
                    f"Unwanted medals: {unwanted_medals_found}, " +
                    f"More medals available: {arrow_result['has_more_medals']}")
        
    except Exception as e:
        logging.error(f"Error in profile analysis: {str(e)}")
        logging.error(traceback.format_exc())
        print("PROFILE_ANALYSIS_RESULT=0")
        print("PROFILE_BUTTON_FOUND=0") 
        print("FOUR_PLUS_MEDALS_FOUND=0")
        print("FIVE_YEAR_MEDAL_FOUND=0")
        print("UNWANTED_MEDALS_FOUND=0")
        print("CLICK_TO_SEE_MORE_MEDALS=0")
        print(f"PROFILE_ANALYSIS_ERROR={str(e)}")

def check_for_unwanted_medals(detected_medals):
    """
    Check if any unwanted medals are in the detected medals list.
    
    Args:
        detected_medals: List of detected medal names
        
    Returns:
        bool: True if unwanted medals found, False otherwise
    """
    # List of unwanted medal templates
    unwanted_medals = ["hydra-pin", "aces-high-pin"]
    
    # Check if any unwanted medals are in the detected list
    for medal in detected_medals:
        for unwanted in unwanted_medals:
            if unwanted in medal:
                logging.info(f"Unwanted medal detected: {medal}")
                return True
                
    return False

def detect_precise_medal_arrow(click_x, click_y, screenshot_path=None, visualization=None):
    """
    Detect the medal arrow using precise offset from the original click position.
    Also analyzes color characteristics to determine if the arrow is active or inactive.
    
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
        "is_active": False
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
        
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_regions")
        os.makedirs(debug_dir, exist_ok=True)
        
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
            
            # Draw on visualization if provided
            if visualization is not None:
                # Adjust coordinates for visualization (which is the profile_roi)
                viz_x = max_loc[0]
                viz_y = max_loc[1]
                
                # Use green for active arrows, red for inactive
                color = (0, 255, 0) if is_active else (0, 0, 255)
                
                cv2.rectangle(visualization, 
                             (viz_x, viz_y),
                             (viz_x + w, viz_y + h),
                             color, 2)
                cv2.putText(visualization, 
                           f"{'Active' if is_active else 'Inactive'} Arrow ({max_val:.2f})", 
                           (viz_x, viz_y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Save debug images
            timestamp = int(time.time())
            
            # Save the detected arrow region
            arrow_found_region = arrow_region[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
            arrow_path = os.path.join(debug_dir, 
                                     f"medal_arrow_precise_{timestamp}_{max_val:.2f}_{'active' if is_active else 'inactive'}.png")
            cv2.imwrite(arrow_path, arrow_found_region)
            
            # Log detection results
            status = "active" if is_active else "inactive"
            # Store the absolute coordinates for returning to AHK
            result["arrow_x"] = arrow_x + max_loc[0]
            result["arrow_y"] = absolute_y
            logging.info(f"Medal arrow detected ({status}) with confidence {max_val:.2f} at absolute position {result['arrow_x']},{result['arrow_y']}")
            
        return result
        
    except Exception as e:
        logging.error(f"Error detecting precise medal arrow: {str(e)}")
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
        # Active arrows are typically brighter and have more contrast
        brightness_threshold = 125  # Lowered from 160 based on observed active arrow brightness
        contrast_threshold = 25     # Adjust based on your observations
        
        # If we have very high contrast (>90), consider it active regardless of brightness
        # This catches arrows that have strong contrast but lower overall brightness
        high_contrast_override = contrast > 90
        
        is_active = high_contrast_override or ((mean_brightness >= brightness_threshold) and (contrast >= contrast_threshold))
        
        return is_active
        
    except Exception as e:
        logging.error(f"Error analyzing arrow activity: {str(e)}")
        # Default to considering it active if analysis fails (safer to check than to skip)
        return True

def batch_analyze_profiles(scoreboard_data):
    """
    Analyze multiple player profiles from scoreboard data.
    
    Args:
        scoreboard_data: List of dicts with player data including click coordinates
        
    Returns:
        Dict with results for all analyzed profiles
    """
    results = {}
    
    for player in scoreboard_data:
        player_id = player.get("nickname", f"player_{len(results)}")
        logging.info(f"Analyzing profile for player: {player_id}")
        
        click_x = player.get("x", 0)
        click_y = player.get("y", 0)
        
        # Individual results will be printed, but we also collect them
        analyze_profile(click_x, click_y)
        
        # You could also add code here to parse the printed results and collect them
        # or modify analyze_profile to return a dict with the results
        
    return results