; CS2 Automation - Optimized Matchmaking Module
; Handles waiting for match to be found and loaded

; Check if we're still searching for a match (CANCEL SEARCH button visible)
IsSearching() {
    ; Check for red CANCEL SEARCH button at bottom right
    cancelSearchX := 1695  ; Updated to your specific coordinates
    cancelSearchY := 1030
    
    try {
        cancelColor := PixelGetColor(cancelSearchX, cancelSearchY)
        
        ; Extract RGB values
        r := (cancelColor >> 16) & 0xFF
        g := (cancelColor >> 8) & 0xFF
        b := cancelColor & 0xFF
        
        ; Red button detection - handle both normal (#c3553c) and darkened (#662022) states
        ; More robust reddish detection - any color with high red component and low green/blue
        if (r > 80 && r > g * 1.5 && r > b * 1.5) {
            return true
        }
    } catch Error as e {
        LogMessage("Error checking search status: " e.Message)
    }
    
    return false
}

; Existing function, modified to return "fatal" when a fatal error is detected
CheckForMatchmakingFailure() {
    
    try {
        ; Take a screenshot
        ;CaptureScreenshot()
        ; Sleep 800  ; Wait for screenshot to be saved
        
        ; Run Python detector
        result := RunPythonDetector("error")
        LogMessage("Error detection result: " result)
        
        ; Enhanced parsing logic
        if InStr(result, "ERROR_DETECTION_RESULT=1") {
            LogMessage("Error dialog detected positively!")
            
            ; Check if this is error_dialog_1, 2, or 3 (the fatal error)
            if InStr(result, "ERROR_TYPE=fatal") {
                LogMessage("FATAL ERROR DIALOG DETECTED! Will exit script after dismissal.")
                
                ; Press Escape to dismiss the dialog
                Send "{Escape}"
                Sleep 500
                Send "{Escape}"  ; Try a second time
                
                ; Display message box to inform user
                ; MsgBox("Fatal error detected in CS2. The script will now exit.`n`nPlease restart CS2 manually.", "Fatal Error", 48)
                
                ; Signal that we need to exit
                return "fatal"
            }
            
            ; Parse coordinates for regular errors
            coordPos := InStr(result, "ERROR_COORDS=")
            if (coordPos > 0) {
                coordsStr := SubStr(result, coordPos + 13) ; 13 is length of "ERROR_COORDS="
                coordsStr := RegExReplace(coordsStr, "\r?\n.*", "") ; Remove anything after the line
                
                coords := StrSplit(coordsStr, ",")
                if (coords.Length = 2) {
                    buttonX := Integer(coords[1])
                    buttonY := Integer(coords[2])
                    
                    ; Check for special coordinates (-1, -1) that indicate to use Escape key
                    if (buttonX = -1 && buttonY = -1) {
                        Send "{Escape}"
                        Sleep 500
                        ; Send a second Escape just to be sure
                        Send "{Escape}"
                    } else {
                        ; Use the detected coordinates
                        Click buttonX, buttonY
                        Sleep 500
                        ; Try a second click to be sure
                        Click buttonX, buttonY
                    }
                    
                    return true
                }
            }
            
            ; Fallback to using Escape key if coordinates couldn't be parsed
            Send "{Escape}"
            Sleep 500
            Send "{Escape}"  ; Try again
            
            return true
        }
        
        return false
    } catch Error as e {
        LogMessage("Error in detection: " e.Message)
        return false
    }
}

; New function to check for Spectate button using pixel color detection
IsSpectateButtonVisible() {
    ; Three key points to check on the spectate button's camera icon
    point1X := 1587  ; Upper-left corner
    point1Y := 1026
    
    point2X := 1596  ; Middle point
    point2Y := 1032
    
    point3X := 1606  ; Lower-right corner
    point3Y := 1039
    
    try {
        ; Get colors at all three points
        color1 := PixelGetColor(point1X, point1Y)
        color2 := PixelGetColor(point2X, point2Y)
        color3 := PixelGetColor(point3X, point3Y)
        
        ; Function to check if a color is whitish (high values in all RGB channels)
        IsWhitish(color) {
            r := (color >> 16) & 0xFF
            g := (color >> 8) & 0xFF
            b := color & 0xFF
            
            ; All channels should be high (above 200) for white
            return (r > 200 && g > 200 && b > 200)
        }
        
        ; Check if all three points are whitish
        if (IsWhitish(color1) && IsWhitish(color2) && IsWhitish(color3)) {
            return true
        }
        
        return false
    } catch Error as e {
        LogMessage("Error checking spectate button colors: " e.Message)
        return false
    }
}

; Optimized match outcome detection with direct pixel color method
WaitForMatchOutcome() {
    LogMessage("Waiting for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := 90000  ; 10 minutes in milliseconds
    
    ; Time to wait before starting error checks (allowing time for match loading)
    initialErrorWait := 1000  ; 10 seconds
    errorCheckInterval := 3000  ; Check for errors every 3 seconds after initial wait
    lastErrorCheckTime := 0
    
    ; Add a counter for consecutive error checks
    consecutiveErrorChecks := 0
    maxConsecutiveErrorChecks := 6  ; Maximum number of consecutive error checks before giving up
    
    ; Flag to track if spectate button detection is successful
    spectateButtonClicked := false
    
    LogMessage("Match detection timeout set to " timeout / 1000 " seconds")
    LogMessage("Will wait " initialErrorWait / 1000 " seconds after Cancel Search disappears before checking for errors")
    
    ; Phase tracking: 0 = searching, 1 = connecting/loading
    currentPhase := 0
    searchingEndTime := 0
    
    ; Spectate button click coordinates
    spectateButtonX := 1596
    spectateButtonY := 1032
    
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
        
        ; Make sure CS2 window is active
        if !WinActive("Counter-Strike") {
            LogMessage("CS2 window is no longer active")
            WinActivate "Counter-Strike"
            Sleep 1000
        }
        
        ; Check if we're in searching state
        if (IsSearching()) {
            if (currentPhase != 0) {
                LogMessage("Returned to searching state, resetting phase")
                currentPhase := 0
                spectateButtonClicked := false  ; Reset this flag when we go back to searching
                consecutiveErrorChecks := 0     ; Reset error check counter when we go back to searching
            }
            
            ; During search phase, we log less frequently and don't take screenshots
            if (Mod(A_Index, 10) = 0) {
                LogMessage("Still searching for match... " elapsedTime / 1000 " seconds elapsed")
            }
            
            ; Sleep 2000  ; Check less frequently during search phase
            continue
        } else if (currentPhase = 0) {
            ; We just transitioned from searching to connecting/loading
            currentPhase := 1
            searchingEndTime := A_TickCount
            LogMessage("Search phase ended, now in connecting/loading phase after " (searchingEndTime - startTime) / 1000 " seconds")
            lastErrorCheckTime := searchingEndTime  ; Initialize for first error check timing
            consecutiveErrorChecks := 0  ; Reset the counter when entering loading phase
        }
        
        ; First priority: Check for Spectate button using pixel color method (only if we haven't clicked it yet)
        if (!spectateButtonClicked && IsSpectateButtonVisible()) {
            LogMessage("Successfully joined match! Spectate button detected via pixel color method")
            
            ; Click the spectate button at the predefined coordinates
            LogMessage("Clicking spectator button at " spectateButtonX ", " spectateButtonY)
            Click spectateButtonX, spectateButtonY
            Sleep 500
            Click spectateButtonX, spectateButtonY  ; Try a second click for reliability
            Sleep 500
            
            ; Set flag to indicate we've successfully clicked the button
            spectateButtonClicked := true
            
            ; Return success immediately - no need to continue with error checking
            return "success"
        }
        
        ; Log progress during loading phase (less frequently)
        if (Mod(A_Index, 5) = 0 && !spectateButtonClicked) {
            timeInLoadingPhase := (A_TickCount - searchingEndTime) / 1000
            LogMessage("In loading phase... " timeInLoadingPhase " seconds elapsed since search ended")
        }
        
        ; Second priority: Check for error dialogs, but only after the initial wait period
        ; Only do this if we haven't detected and clicked the spectate button yet
        if (!spectateButtonClicked) {
            timeInLoadingPhase := A_TickCount - searchingEndTime
            if (timeInLoadingPhase > initialErrorWait && currentTime - lastErrorCheckTime > errorCheckInterval) {
                LogMessage("Taking screenshot to check for error dialog...")
                CaptureScreenshot()
                Sleep 800  ; Wait for screenshot to be saved
                lastErrorCheckTime := currentTime
                
                ; Check for failure dialog
                errorResult := CheckForMatchmakingFailure()
                if (errorResult) {
                    if (errorResult = "fatal") {
                        LogMessage("FATAL matchmaking error detected - exiting script")
                        return "fatal_error"
                    } else {
                        LogMessage("Matchmaking failure detected and handled")
                        return "failure"
                    }
                } else {
                    ; Increment consecutive error checks counter
                    consecutiveErrorChecks++
                    LogMessage("No error dialog found. Consecutive error checks: " consecutiveErrorChecks "/" maxConsecutiveErrorChecks)
                    
                    ; Check if we've reached the maximum consecutive error checks
                    if (consecutiveErrorChecks >= maxConsecutiveErrorChecks) {
                        LogMessage("Reached maximum consecutive error checks (" maxConsecutiveErrorChecks "). Assuming match failure.")
                        return "failure"
                    }
                }
            }
        }
        
        ; Short sleep between checks to avoid excessive CPU usage
        Sleep 500
    }
    
    return "unknown"  ; Should never reach here
}