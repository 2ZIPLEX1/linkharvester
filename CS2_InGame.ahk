; CS2 Automation - Simplified In-Game Module
; Handles actions once a match has been successfully joined

; Process the current match (view players, capture data, etc.)
ProcessMatch() {
    LogMessage("Processing match...")
    
    ; Wait a few seconds for the match to fully load
    Sleep 5000
    
    ; View the player list using Tab
    ViewPlayerList()
    
    ; Return to main menu using ESC
    ReturnToMainMenu()
    
    LogMessage("Match processing completed")
    return true
}

; View the player list using Tab
ViewPlayerList() {
    LogMessage("Viewing player list...")
    
    ; Make sure CS2 is the active window
    if !WinActive("Counter-Strike") {
        WinActivate "Counter-Strike"
        Sleep 1000
    }
    
    ; Press Esc to view scoreboard
    LogMessage("Pressing Escape to view scoreboard...")
    Send "{Escape}"
    ; Sleep 2000
    
    ; Take screenshot of player list
    LogMessage("Taking screenshot of player list...")
    CaptureScreenshot()
    
    ; Analyze the scoreboard to find player rows
    AnalyzeScoreboard()
    
    ; Release Tab
    ; Send "{Tab up}"
    ; Sleep 500
    
    return true
}

; Return to main menu by leaving the match
ReturnToMainMenu() {
    LogMessage("Returning to main menu by leaving match...")
    
    ; Click the Leave Match button
    leaveMatchX := 1170
    leaveMatchY := 130
    LogMessage("Clicking Leave Match button at " leaveMatchX "," leaveMatchY)
    Click leaveMatchX, leaveMatchY
    Sleep 1000
    
    ; Click OK on the confirmation dialog
    confirmX := 1100
    confirmY := 600
    LogMessage("Clicking OK to confirm at " confirmX "," confirmY)
    Click confirmX, confirmY
    Sleep 3000
    
    ; Take screenshot to confirm we're back at the main menu
    CaptureScreenshot()
    
    ; Wait a bit longer for the main menu to fully load
    Sleep 2000
    
    return true
}

AnalyzeScoreboard() {
    LogMessage("Analyzing scoreboard player rows...")
    
    ; Take a screenshot
    CaptureScreenshot()
    Sleep 1000  ; Wait for screenshot to be saved
    
    ; Run Python detector
    result := RunPythonDetector("scoreboard")
    LogMessage("Scoreboard detection result: " result)
    
    ; Check if detection was successful
    if !InStr(result, "DETECTION_RESULT=1") {
        LogMessage("Failed to detect scoreboard rows")
        return false
    }
    
    ; Create empty objects for the coordinates
    ct := {found: false, x: 0, y: 0}
    t := {found: false, x: 0, y: 0}
    
    ; Parse CT coordinates
    if InStr(result, "CT_FIRST_ROW_COORDS=") {
        ctText := RegExMatch(result, "CT_FIRST_ROW_COORDS=(\d+),(\d+)", &ctMatch)
        if (ctMatch) {
            ct.found := true
            ct.x := Integer(ctMatch[1])
            ct.y := Integer(ctMatch[2])
            LogMessage("Found CT first player row at " ct.x "," ct.y)
        }
    }
    
    ; Parse T coordinates - completely separate from CT parsing
    if InStr(result, "T_FIRST_ROW_COORDS=") {
        tText := RegExMatch(result, "T_FIRST_ROW_COORDS=(\d+),(\d+)", &tMatch)
        if (tMatch) {
            t.found := true
            t.x := Integer(tMatch[1])
            t.y := Integer(tMatch[2])
            LogMessage("Found T first player row at " t.x "," t.y)
        }
    }
    
    ; Verify we found at least one team's rows
    if (!ct.found && !t.found) {
        LogMessage("Could not determine row coordinates for either team")
        return false
    }
    
    ; For testing, click the first row of each team if found
    if (ct.found) {
        LogMessage("Testing: Clicking first CT row at " ct.x "," ct.y)
        Click ct.x+10, ct.y+10
        Sleep 1000
        ; Take screenshot after CT player click
        LogMessage("Taking screenshot after CT player click...")
        CaptureScreenshot()
        Sleep 500
        Send "{Escape}"
        Sleep 500  ; Wait a bit after pressing Escape
    }
    
    if (t.found) {
        LogMessage("Testing: Clicking first T row at " t.x "," t.y)
        Click t.x+10, t.y+10
        Sleep 1000
        ; Take screenshot after T player click
        LogMessage("Taking screenshot after T player click...")
        CaptureScreenshot()
        Sleep 500
        Send "{Escape}"
        Sleep 500  ; Wait a bit after pressing Escape
    }
    
    return true
}