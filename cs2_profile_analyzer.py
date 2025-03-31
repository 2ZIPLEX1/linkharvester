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
from cs2_detect import get_latest_screenshot

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
    Unified profile analysis function that orchestrates all detection steps.
    This function analyzes the entire profile details region based on the original click coordinates.
    
    Args:
        click_x: X-coordinate of original click position on player in scoreboard
        click_y: Y-coordinate of original click position on player in scoreboard
        screenshot_path: Optional path to screenshot to use
        
    Returns:
        Complete analysis with decision on whether to proceed with Steam profile check
    """
    try:
        # Get the profile ROI from the screenshot
        profile_roi, roi_x, roi_y = get_profile_roi(click_x, click_y, screenshot_path)
        if profile_roi is None:
            # Error already logged and printed by get_profile_roi
            return
        
        # Create a visualization image for our detections
        visualization = profile_roi.copy()
        
        # Detect profile button
        profile_button_result = detect_profile_button_in_roi(profile_roi, roi_x, roi_y, visualization)
        if not profile_button_result["found"]:
            # If no profile button found, exit early
            logging.info("No profile button detected in profile details")
            print("PROFILE_ANALYSIS_RESULT=1")
            print("PROFILE_BUTTON_FOUND=0")
            print("DECISION=SKIP")
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
        
        # Make decision based on medal criteria
        decision_result = make_medal_decision(
            medal_result["count"], 
            medal_result["has_5year_coin"], 
            arrow_result["has_more_medals"]
        )
        
        # Output results
        print("PROFILE_ANALYSIS_RESULT=1")
        print(f"MEDAL_COUNT={medal_result['count']}")
        print(f"HAS_5YEAR_COIN={1 if medal_result['has_5year_coin'] else 0}")
        print(f"HAS_MORE_MEDALS={1 if arrow_result['has_more_medals'] else 0}")
        print(f"MEETS_CRITERIA={1 if decision_result['meets_criteria'] else 0}")
        
        # Include individual medal information
        for medal_name in medal_result["detected_medals"]:
            print(f"MEDAL_DETECTED={medal_name}")
        
        # Final decision
        if decision_result["meets_criteria"]:
            print("DECISION=PROCEED")
        else:
            print("DECISION=SKIP")
        
        logging.info(f"Profile analysis complete: {medal_result['count']} medals, " +
                    f"5-year coin: {medal_result['has_5year_coin']}, " +
                    f"Decision: {'PROCEED' if decision_result['meets_criteria'] else 'SKIP'}")
        
    except Exception as e:
        logging.error(f"Error in profile analysis: {str(e)}")
        logging.error(traceback.format_exc())
        print("PROFILE_ANALYSIS_RESULT=0")
        print(f"PROFILE_ANALYSIS_ERROR={str(e)}")
        print("DECISION=SKIP")  # Default to skip on error

def detect_precise_medal_arrow(click_x, click_y, screenshot_path=None, visualization=None):
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
        "confidence": 0.0
    }
    
    try:
        # Get the latest screenshot
        screenshot_path = get_latest_screenshot()
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
        # Arrow size is 8px wide by 14px high
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
        
        if max_val >= 0.7:  # Threshold for matching
            result["has_more_medals"] = True
            result["confidence"] = max_val
            
            h, w = arrow_template.shape[:2]
            
            # Calculate absolute Y position in the original image
            absolute_y = arrow_min_y + max_loc[1]
            
            # Draw on visualization if provided
            if visualization is not None:
                # Adjust coordinates for visualization (which is the profile_roi)
                viz_x = max_loc[0]
                viz_y = max_loc[1]
                
                cv2.rectangle(visualization, 
                             (viz_x, viz_y),
                             (viz_x + w, viz_y + h),
                             (0, 255, 0), 2)
                cv2.putText(visualization, f"More Medals ({max_val:.2f})", 
                           (viz_x, viz_y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Save debug images
            timestamp = int(time.time())
            
            # Save the detected arrow region
            arrow_found_region = arrow_region[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
            arrow_path = os.path.join(debug_dir, f"medal_arrow_precise_{timestamp}_{max_val:.2f}.png")
            cv2.imwrite(arrow_path, arrow_found_region)
            
            # Save part of the original image with arrow highlighted
            debug_img = img.copy()
            cv2.rectangle(debug_img, 
                         (arrow_x + max_loc[0], absolute_y),
                         (arrow_x + max_loc[0] + w, absolute_y + h),
                         (0, 255, 0), 2)
            debug_path = os.path.join(debug_dir, f"medal_arrow_context_{timestamp}.jpg")
            cv2.imwrite(debug_path, debug_img[max(0, absolute_y-50):min(img_height, absolute_y+50), 
                                           max(0, arrow_x-50):min(img_width, arrow_x+50)])
            
            logging.info(f"Medal arrow detected with confidence {max_val:.2f} at absolute position {arrow_x+max_loc[0]},{absolute_y}")
            logging.info(f"Saved arrow detection images to {debug_dir}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error detecting precise medal arrow: {str(e)}")
        logging.error(traceback.format_exc())
        return result

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