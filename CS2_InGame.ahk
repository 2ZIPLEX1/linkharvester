; CS2 Automation - Fixed In-Game Module
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
    
    ; Create empty objects for the coordinates
    ct := {found: false, x: 0, y: 0}
    t := {found: false, x: 0, y: 0}
    
    ; COMPLETELY SEPARATE APPROACH - Run two different Python commands
    
    ; 1. First get CT coordinates with a separate command
    LogMessage("Getting CT player coordinates...")
    CaptureScreenshot()
    Sleep 1000
    
    ctResult := RunPythonDetector("ct")
    LogMessage("CT detection result: " ctResult)
    
    if InStr(ctResult, "CT_DETECTION_RESULT=1") {
        ; Extract X coordinate
        if RegExMatch(ctResult, "CT_ROW_X=(\d+)", &ctXMatch) {
            ctX := ctXMatch[1]
            LogMessage("DEBUG: CT raw X value: " ctX)
            
            ; Extract Y coordinate
            if RegExMatch(ctResult, "CT_ROW_Y=(\d+)", &ctYMatch) {
                ctY := ctYMatch[1]
                LogMessage("DEBUG: CT raw Y value: " ctY)
                
                ; Set CT coordinates
                ct.x := ctX
                ct.y := ctY
                ct.found := true
                LogMessage("Found CT first player row at " ct.x "," ct.y)
            }
        }
    }
    
    ; 2. Then get T coordinates with a completely separate command
    LogMessage("Getting T player coordinates...")
    CaptureScreenshot() 
    Sleep 1000
    
    tResult := RunPythonDetector("t")
    LogMessage("T detection result: " tResult)
    
    if InStr(tResult, "T_DETECTION_RESULT=1") {
        ; Extract X coordinate
        if RegExMatch(tResult, "T_ROW_X=(\d+)", &tXMatch) {
            tX := tXMatch[1]
            LogMessage("DEBUG: T raw X value: " tX)
            
            ; Extract Y coordinate
            if RegExMatch(tResult, "T_ROW_Y=(\d+)", &tYMatch) {
                tY := tYMatch[1]
                LogMessage("DEBUG: T raw Y value: " tY)
                
                ; Set T coordinates
                t.x := tX
                t.y := tY
                t.found := true
                LogMessage("Found T first player row at " t.x "," t.y)
            }
        }
    }
    
    ; Add debug output
    LogMessage("DEBUG: CT found=" ct.found ", T found=" t.found)
    if (ct.found)
        LogMessage("DEBUG: Final CT coordinates x=" ct.x ", y=" ct.y)
    if (t.found)
        LogMessage("DEBUG: Final T coordinates x=" t.x ", y=" t.y)
    
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
        Click ct.x+10, ct.y+10 ; Click to exit Profile details
    }
    
    if (t.found) {
        LogMessage("Testing: Clicking first T row at " t.x "," t.y)
        Click t.x+10, t.y+10
        Sleep 1000
        ; Take screenshot after T player click
        LogMessage("Taking screenshot after T player click...")
        CaptureScreenshot()
        Sleep 500
        Click t.x+10, t.y+10 ; Click to exit Profile details
        Sleep 500
    }
    
    return true
}