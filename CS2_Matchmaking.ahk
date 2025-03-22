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
        ; The OK button coordinates
        okButtonX := 877
        okButtonY := 458
        
        ; Check if we have a light-colored button (usually white/light gray text)
        okButtonColor := PixelGetColor(okButtonX, okButtonY)
        LogMessage("OK button color: " okButtonColor)
        
        ; Extract RGB values for brightness calculation
        r := (okButtonColor >> 16) & 0xFF
        g := (okButtonColor >> 8) & 0xFF
        b := okButtonColor & 0xFF
        
        ; Calculate brightness
        brightness := (r * 0.299 + g * 0.587 + b * 0.114)
        
        ; If we detect a bright button in the error position
        if (brightness > 160) {
            LogMessage("Detected potential OK button for error dialog")
            
            ; Click the button
            LogMessage("Clicking OK button at " okButtonX "," okButtonY)
            Click okButtonX, okButtonY
            Sleep 1000
            
            ; Take a screenshot
            CaptureScreenshot()
            
            return true
        }
    } catch Error as e {
        LogMessage("Error checking for matchmaking failure: " e.Message)
    }
    
    return false
}

; Simplified check for spectate button
CheckForSpectateButton() {
    try {
        ; Center of the SPECTATE text (for clicking)
        spectateX := 1640
        spectateY := 1031
        
        ; Get color at this point
        textColor := PixelGetColor(spectateX, spectateY)
        LogMessage("SPECTATE text color: " textColor)
        
        ; Extract RGB values for brightness calculation
        r := (textColor >> 16) & 0xFF
        g := (textColor >> 8) & 0xFF
        b := textColor & 0xFF
        
        ; Calculate brightness
        brightness := (r * 0.299 + g * 0.587 + b * 0.114)
        
        ; If we detect bright text (usually white/light gray)
        if (brightness > 160) {
            LogMessage("Detected potential SPECTATE button")
            
            ; Take a screenshot
            CaptureScreenshot()
            
            return true
        }
    } catch Error as e {
        LogMessage("Error checking for spectate button: " e.Message)
    }
    
    return false
}

; Simplified match outcome detection
WaitForMatchOutcome() {
    LogMessage("Waiting for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := 180000  ; 3 minutes in milliseconds (minimum)
    
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
            
            ; Click the spectator button
            buttonX := 1640
            buttonY := 1031
            
            LogMessage("Clicking spectator button at " buttonX ", " buttonY)
            Click buttonX, buttonY
            Sleep 1000
            
            ; Take another screenshot after clicking
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