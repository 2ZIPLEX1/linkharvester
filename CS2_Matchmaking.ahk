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

; Check for spectator button with improved detection
CheckForSpectateButton() {
    Global CS2_CONFIG
    
    try {
        ; Get coordinates for the spectate button area you provided
        spectateLeftX := 1577  ; upper-left X
        spectateLeftY := 1008  ; upper-left Y
        spectateRightX := 1699 ; lower-right X
        spectateRightY := 1055 ; lower-right Y
        
        ; Camera icon starts at 1586,1025
        cameraIconX := 1586
        cameraIconY := 1025
        
        ; Center of the SPECTATE text (for clicking)
        spectateX := 1640
        spectateY := 1031
        
        ; Sample multiple points in the spectate button area for more reliable detection
        cameraColor := PixelGetColor(cameraIconX, cameraIconY)
        spectateTextColor := PixelGetColor(spectateX, spectateY)
        
        ; Log the detected colors for debugging
        LogMessage("Camera icon color: " cameraColor)
        LogMessage("SPECTATE text color: " spectateTextColor)
        
        ; Take a screenshot for debugging
        CaptureFullscreenScreenshot()
        
        ; Check for contrast between icon/text and surrounding area
        ; Sample points above and below the button
        aboveColor := PixelGetColor(spectateX, spectateLeftY - 10)
        belowColor := PixelGetColor(spectateX, spectateRightY + 10)
        
        ; Check if we have light text on dark background (common in CS2 UI)
        if (IsLightColor(spectateTextColor) && IsDarkColor(aboveColor)) {
            LogMessage("Detected potential SPECTATE button (light text)")
            
            ; Additional check to confirm it's really the spectate button
            ; Check if camera icon area has a different color than the text
            if (!IsSimilarColor(cameraColor, spectateTextColor, 40)) {
                LogMessage("Confirmed SPECTATE button with camera icon check")
                return true
            }
        }
        
        ; Alternative detection - check for specific color patterns
        ; If the button has a consistent background like a rectangle
        leftSideColor := PixelGetColor(spectateLeftX + 5, spectateY)
        rightSideColor := PixelGetColor(spectateRightX - 5, spectateY)
        
        if (IsSimilarColor(leftSideColor, rightSideColor, 30) && 
            !IsSimilarColor(leftSideColor, aboveColor, 50)) {
            LogMessage("Detected SPECTATE button by button shape")
            return true
        }
    } catch Error as e {
        LogMessage("Error checking for spectate button: " e.Message)
    }
    
    return false
}

; Improved match outcome detection
WaitForMatchOutcome() {
    Global CS2_CONFIG
    
    LogMessage("Waiting for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := CS2_CONFIG["max_wait_for_match"] * 1000  ; Convert to milliseconds
    
    ; Increase timeout for more reliable detection
    if (timeout < 180000)  ; If less than 3 minutes
        timeout := 180000  ; Set to 3 minutes minimum
    
    LogMessage("Match detection timeout set to " timeout / 1000 " seconds")
    
    loop {
        ; Check if user requested exit
        if (ShouldExit()) {
            LogMessage("Script exit requested during match outcome detection")
            return "aborted"
        }
        
        ; Check if we've exceeded the timeout
        currentTime := A_TickCount
        elapsedTime := currentTime - startTime
        
        if (elapsedTime > timeout) {
            LogMessage("Timed out waiting for match outcome after " elapsedTime / 1000 " seconds")
            return "timeout"
        }
        
        ; Log progress periodically
        if (Mod(A_Index, 5) = 0) {
            LogMessage("Still waiting for match outcome... " elapsedTime / 1000 " seconds elapsed")
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
            CaptureFullscreenScreenshot()
        }
        
        ; First check if we're in searching state
        if (IsSearching()) {
            LogMessage("Still searching for match... waiting")
            Sleep 3000
            continue
        }
        
        ; Check for match ready screen (the green "YOUR MATCH IS READY!" popup)
        if (IsMatchReadyScreen()) {
            LogMessage("Match is ready! Waiting for it to transition to the actual match...")
            
            ; We're now in a transition state - wait longer between checks
            ; since we know we need to wait for the match to fully load
            Sleep 8000  ; Wait longer when we see the ready screen
            
            ; Take another screenshot after waiting to see if we've transitioned
            CaptureFullscreenScreenshot()
            continue    ; Continue waiting for spectate button
        }
        
        ; Check for success (Spectate button) - using our improved detection
        if (CheckForSpectateButton()) {
            LogMessage("Successfully joined match!")
            
            ; Click the spectator button (using the center of the button area)
            buttonX := 1640  ; Center X of SPECTATE text
            buttonY := 1031  ; Center Y of SPECTATE text
            
            LogMessage("Clicking spectator button at " buttonX ", " buttonY)
            Click buttonX, buttonY
            Sleep 1000
            
            ; Take another screenshot after clicking
            CaptureFullscreenScreenshot()
            
            return "success"
        }
        
        ; Check for failure dialog
        if (CheckForMatchmakingFailure()) {
            LogMessage("Matchmaking failure detected and handled")
            return "failure"
        }
        
        ; Wait before next check - shorter interval for more responsive detection
        Sleep 2000
    }
    
    return "unknown"  ; Should never reach here
}

; Detect "YOUR MATCH IS READY!" screen
IsMatchReadyScreen() {
    try {
        ; Based on your screenshot, check for the green highlight and text
        ; Sample points around the "YOUR MATCH IS READY!" text
        readyTextX := 727    ; Center X of "YOUR MATCH IS READY!"
        readyTextY := 300    ; Center Y of text
        
        ; Check for bright green border
        greenBorderTopX := 727
        greenBorderTopY := 211   ; Top of green border
        greenBorderBottomY := 390 ; Bottom of green border
        
        ; Get colors at these points
        textColor := PixelGetColor(readyTextX, readyTextY)
        topBorderColor := PixelGetColor(greenBorderTopX, greenBorderTopY)
        bottomBorderColor := PixelGetColor(greenBorderTopX, greenBorderBottomY)
        
        LogMessage("Match ready text color: " textColor)
        LogMessage("Top border color: " topBorderColor)
        LogMessage("Bottom border color: " bottomBorderColor)
        
        ; Check if we detect bright green (looking for color like #00FF00 or similar)
        if (IsGreenColor(topBorderColor) && IsGreenColor(bottomBorderColor)) {
            LogMessage("Detected green border of match ready screen")
            
            ; Take a screenshot for verification
            CaptureFullscreenScreenshot()
            
            ; Just log that we saw it, no need to click
            LogMessage("Match ready screen detected - waiting for it to transition to the match")
            
            return true
        }
    } catch Error as e {
        LogMessage("Error checking for match ready screen: " e.Message)
    }
    
    return false
}

; Helper function to detect green colors
IsGreenColor(colorHex) {
    try {
        ; Convert hex string to number if needed
        if (Type(colorHex) = "String" && SubStr(colorHex, 1, 2) = "0x")
            color := Integer("0x" . SubStr(colorHex, 3))
        else if (Type(colorHex) = "String")
            color := Integer("0x" . colorHex)
        else
            color := colorHex
            
        ; Extract RGB values
        r := (color >> 16) & 0xFF
        g := (color >> 8) & 0xFF
        b := color & 0xFF
        
        ; Check if green component is significantly higher than others (bright green)
        return (g > 180) && (g > r * 1.5) && (g > b * 1.5)
    } catch Error as e {
        LogMessage("Error in IsGreenColor: " e.Message)
        return false
    }
}