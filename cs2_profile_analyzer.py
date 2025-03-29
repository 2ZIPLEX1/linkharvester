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
        
        # Check for medal arrow (more medals indicator)
        arrow_result = detect_medal_arrow_in_roi(profile_roi, visualization)
        
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