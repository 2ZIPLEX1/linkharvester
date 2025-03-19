; CS2 Automation - Matchmaking Module
; Handles waiting for match to be found and loaded

; Function to check if we're in searching state (CANCEL SEARCH button visible)
IsSearching() {
    ; Check for red CANCEL SEARCH button at bottom right
    cancelSearchX := 1278
    cancelSearchY := 785
    
    try {
        cancelColor := PixelGetColor(cancelSearchX, cancelSearchY)
        LogMessage("Cancel search button area color: " cancelColor)
        
        ; Red button detection (looking for reddish colors)
        if (IsRedColor(cancelColor)) {
            LogMessage("Detected CANCEL SEARCH button - still searching for match")
            return true
        }
    } catch Error as e {
        LogMessage("Error checking search status: " e.Message)
    }
    
    return false
}

; More precise matchmaking failure detection
CheckForMatchmakingFailure() {
    LogMessage("Checking for matchmaking failure dialog...")
    
    try {
        ; Check multiple specific points on the error dialog
        ; Based on the error message layout:
        
        ; Check for the dark semi-transparent dialog overlay
        dialogCenterX := 642
        dialogCenterY := 402
        
        ; The OK button
        okButtonX := 877
        okButtonY := 458
        
        ; Get colors at these points
        dialogColor := PixelGetColor(dialogCenterX, dialogCenterY)
        okButtonColor := PixelGetColor(okButtonX, okButtonY)
        
        ; Log for debugging
        LogMessage("Dialog center color: " dialogColor)
        LogMessage("OK button color: " okButtonColor)
        
        ; Check multiple border points to detect dialog edges
        leftBorderX := 550
        leftBorderY := 400
        rightBorderX := 730 
        rightBorderY := 400
        
        leftColor := PixelGetColor(leftBorderX, leftBorderY)
        rightColor := PixelGetColor(rightBorderX, rightBorderY)
        
        LogMessage("Left border color: " leftColor)
        LogMessage("Right border color: " rightColor)
        
        ; Look for consistent dark/gray color at border points and
        ; dialog center, which indicates the error overlay is present
        if (IsSimilarColor(leftColor, rightColor, 30) && 
            IsDarkColor(leftColor) && 
            IsDarkColor(dialogColor)) {
            
            ; If we detect consistent dark overlay, check the title and OK button
            titleX := 642
            titleY := 352
            titleColor := PixelGetColor(titleX, titleY)
            LogMessage("Title area color: " titleColor)
            
            ; For the matchmaking error, we should see contrasting colors
            ; between the text elements and the dark background
            if (IsLightColor(okButtonColor) || IsLightColor(titleColor)) {
                LogMessage("Detected matchmaking failure dialog with high confidence")
                
                ; Click the OK button
                LogMessage("Clicking OK button at " okButtonX "," okButtonY)
                Click okButtonX, okButtonY
                Sleep 1000
                
                CaptureScreenshot()
                
                return true
            }
        }
    } catch Error as e {
        LogMessage("Error checking for matchmaking failure: " e.Message)
    }
    
    return false
}

; Check for spectator button (success case)
CheckForSpectateButton() {
    Global CS2_CONFIG
    
    try {
        ; Get coordinates from config
        spectateX := CS2_CONFIG["spectator_button_x"]
        spectateY := CS2_CONFIG["spectator_button_y"]
        
        spectateColor := PixelGetColor(spectateX, spectateY)
        LogMessage("Spectate button color: " spectateColor)
        
        ; Check if color matches expected color for the SPECTATE button
        if (IsColorSimilar(spectateX, spectateY, CS2_CONFIG["spectator_button_color"], CS2_CONFIG["color_tolerance"])) {
            LogMessage("Detected SPECTATE button based on color match")
            
            ; Check surrounding pixels to confirm with contrast check
            aboveColor := PixelGetColor(spectateX, spectateY - 10)
            belowColor := PixelGetColor(spectateX, spectateY + 10)
            
            ; Check for contrast with surrounding pixels
            if (!IsSimilarColor(spectateColor, aboveColor, 30) || 
                !IsSimilarColor(spectateColor, belowColor, 30)) {
                
                LogMessage("Confirmed SPECTATE button with contrast check")
                return true
            }
        }
        
        ; Alternative detection using light color check
        if (IsLightColor(spectateColor)) {
            LogMessage("Detected possible SPECTATE button using brightness check")
            
            ; Check surrounding pixels to confirm
            aboveColor := PixelGetColor(spectateX, spectateY - 10)
            belowColor := PixelGetColor(spectateX, spectateY + 10)
            
            ; If there's contrast between the button text and surroundings
            if (IsDarkColor(aboveColor) || IsDarkColor(belowColor)) {
                LogMessage("Confirmed SPECTATE button with contrast check")
                return true
            }
        }
    } catch Error as e {
        LogMessage("Error checking for spectate button: " e.Message)
    }
    
    return false
}

; Main function to wait for match outcome (success or failure)
WaitForMatchOutcome() {
    Global CS2_CONFIG
    
    LogMessage("Waiting for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := CS2_CONFIG["max_wait_for_match"] * 1000  ; Convert to milliseconds
    
    loop {
        ; Check if user requested exit
        if (ShouldExit()) {
            LogMessage("Script exit requested during match outcome detection")
            return "aborted"
        }
        
        ; Check if we've exceeded the timeout
        if (A_TickCount - startTime > timeout) {
            LogMessage("Timed out waiting for match outcome")
            return "timeout"
        }
        
        ; Make sure CS2 window is active
        if !WinActive("Counter-Strike") {
            LogMessage("CS2 window is no longer active")
            WinActivate "Counter-Strike"
            Sleep 1000
        }
        
        ; Take periodic screenshots
        if (Mod(A_Index, 10) = 0) {
            LogMessage("Taking detection screenshot...")
            CaptureScreenshot()
        }
        
        ; First check if we're in searching state
        if (IsSearching()) {
            LogMessage("Still searching for match... waiting")
            Sleep 3000
            continue
        }
        
        ; Check for success (Spectate button)
        if (CheckForSpectateButton()) {
            LogMessage("Successfully joined match!")
            
            ; Click the spectator button
            LogMessage("Clicking spectator button")
            Click CS2_CONFIG["spectator_button_x"], CS2_CONFIG["spectator_button_y"]
            Sleep 1000
            
            CaptureScreenshot()
            
            return "success"
        }
        
        ; Check for failure dialog
        if (CheckForMatchmakingFailure()) {
            LogMessage("Matchmaking failure detected and handled")
            return "failure"
        }
        
        ; Additional check using Tab key as fallback for success detection
        if (A_Index > 15) {  ; After several checks
            LogMessage("Trying Tab key to check if match started...")
            Send "{Tab down}"
            Sleep 1000
            CaptureScreenshot()
            Send "{Tab up}"
            Sleep 500
            
            ; Note: We don't return success here, just continue checking
            ; to be more certain with visual detection
        }
        
        ; Wait before next check
        Sleep 2000
    }
    
    return "unknown"  ; Should never reach here
}