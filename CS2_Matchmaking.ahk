; CS2 Automation - Simplified Matchmaking Module
; Handles waiting for match to be found and loaded

; Check if we're still searching for a match (CANCEL SEARCH button visible)
IsSearching() {
    ; Check for red CANCEL SEARCH button at bottom right
    cancelSearchX := 1278
    cancelSearchY := 785
    
    try {
        cancelColor := PixelGetColor(cancelSearchX, cancelSearchY)
        LogMessage("Cancel search button area color: " cancelColor)
        
        ; Extract RGB values
        r := (cancelColor >> 16) & 0xFF
        g := (cancelColor >> 8) & 0xFF
        b := cancelColor & 0xFF
        
        ; Red button detection (high red, lower green and blue)
        if (r > 180 && r > g * 1.5 && r > b * 1.5) {
            LogMessage("Detected CANCEL SEARCH button - still searching for match")
            return true
        }
    } catch Error as e {
        LogMessage("Error checking search status: " e.Message)
    }
    
    return false
}

; Check for error dialog with OK button
CheckForMatchmakingFailure() {
    LogMessage("Checking for matchmaking failure dialog...")
    
    try {
        ; Take a screenshot
        CaptureScreenshot()
        Sleep 1000  ; Wait for screenshot to be saved
        
        ; Run Python detector
        result := RunPythonDetector("error")
        LogMessage("Error detection result: " result)
        
        ; Enhanced parsing logic
        if InStr(result, "ERROR_DETECTION_RESULT=1") {
            LogMessage("Error dialog detected positively!")
            
            ; Parse coordinates
            coordPos := InStr(result, "ERROR_COORDS=")
            if (coordPos > 0) {
                coordsStr := SubStr(result, coordPos + 13) ; 13 is length of "ERROR_COORDS="
                coordsStr := RegExReplace(coordsStr, "\r?\n.*", "") ; Remove anything after the line
                
                coords := StrSplit(coordsStr, ",")
                if (coords.Length = 2) {
                    buttonX := Integer(coords[1])
                    buttonY := Integer(coords[2])
                    
                    LogMessage("Clicking OK button at " buttonX "," buttonY)
                    Click buttonX, buttonY
                    Sleep 500
                    ; Try a second click to be sure
                    Click buttonX, buttonY
                    
                    ; Take a verification screenshot
                    CaptureScreenshot()
                    
                    return true
                }
            }
            
            ; Fallback to hardcoded coordinates
            LogMessage("Using hardcoded OK button coordinates")
            Click 1157, 605  ; Center of OK button
            Sleep 500
            Click 1157, 605  ; Try again
            
            ; Take a verification screenshot
            CaptureScreenshot()
            
            return true
        }
        
        return false
    } catch Error as e {
        LogMessage("Error in detection: " e.Message)
        return false
    }
}

; Check for spectate button
CheckForSpectateButton() {
    LogMessage("Checking for spectate button...")
    
    try {
        ; Take a screenshot
        CaptureScreenshot()
        Sleep 1000  ; Wait for screenshot to be saved
        
        ; Run Python detector
        result := RunPythonDetector("spectate")
        LogMessage("Spectate detection result: " result)
        
        ; Enhanced parsing logic
        if InStr(result, "SPECTATE_DETECTION_RESULT=1") {
            LogMessage("Spectate button detected positively!")
            
            ; Parse coordinates
            coordPos := InStr(result, "SPECTATE_COORDS=")
            if (coordPos > 0) {
                coordsStr := SubStr(result, coordPos + 16) ; 16 is length of "SPECTATE_COORDS="
                coordsStr := RegExReplace(coordsStr, "\r?\n.*", "") ; Remove anything after the line
                
                coords := StrSplit(coordsStr, ",")
                if (coords.Length = 2) {
                    LogMessage("Found spectate coordinates: " coords[1] "," coords[2])
                    return true
                }
            }
            
            ; Even if coordinates weren't properly parsed, we detected the button
            LogMessage("Spectate button detected but couldn't parse coordinates")
            return true
        }
    } catch Error as e {
        LogMessage("Error in detection: " e.Message)
    }
    
    return false
}

; Simplified match outcome detection
WaitForMatchOutcome() {
    LogMessage("Waiting for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := 60000  ; 1 minute in milliseconds (minimum)
    
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
        
        ; Log progress every 10 seconds
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
            
            ; Run detector again to get fresh coordinates
            result := RunPythonDetector("spectate")
            
            ; Default coordinates based on your configuration
            buttonX := 1640  ; Center of spectate button X
            buttonY := 1032  ; Center of spectate button Y
            
            ; Try to parse coordinates from result
            coordPos := InStr(result, "SPECTATE_COORDS=")
            if (coordPos > 0) {
                coordsStr := SubStr(result, coordPos + 16)
                coordsStr := RegExReplace(coordsStr, "\r?\n.*", "")
                
                coords := StrSplit(coordsStr, ",")
                if (coords.Length = 2) {
                    buttonX := Integer(coords[1])
                    buttonY := Integer(coords[2])
                    LogMessage("Using detected coordinates: " buttonX "," buttonY)
                }
            }
            
            ; Click the button - add multiple click attempts to ensure it works
            LogMessage("Clicking spectator button at " buttonX ", " buttonY)
            Click buttonX, buttonY
            Sleep 500
            Click buttonX, buttonY  ; Try a second click
            Sleep 500
            
            ; Take a screenshot after clicking
            CaptureScreenshot()
            
            return "success"
        }
        
        ; Check for failure dialog
        if (CheckForMatchmakingFailure()) {
            LogMessage("Matchmaking failure detected and handled")
            return "failure"
        }
        
        ; Wait before next check
        Sleep 2000
    }
    
    return "unknown"  ; Should never reach here
}