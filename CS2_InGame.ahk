; CS2 Automation - Fixed In-Game Module
; Handles actions once a match has been successfully joined

; Process all players from both teams using a single screenshot
ProcessAllPlayers() {
    LogMessage("Starting player processing with single screenshot approach...")
    
    ; Variables to track team positions
    ctFound := false
    ctBaseX := 0
    ctBaseY := 0
    ctPlayers := []
    
    tFound := false
    tBaseX := 0
    tBaseY := 0
    tPlayers := []
    
    ; Player row height (exact 26px as specified)
    playerRowHeight := 26
    
    ; Maximum players to try (generous upper limit for casual matches)
    maxPlayersToCheck := 20
    
    ; ---- STEP 1: Take a SINGLE screenshot of the scoreboard ----
    LogMessage("Taking single screenshot of scoreboard...")
    CaptureScreenshot()
    Sleep 1000  ; Wait for screenshot to be saved
    
    ; Get path to the saved screenshot - we need to create a mechanism to pass this to the Python detector
    LogMessage("Using a single screenshot for all player detection")
    
    ; ---- STEP 2: Find CT team base position using saved screenshot ----
    LogMessage("Finding CT team base position...")
    ctResult := RunPythonDetector("ct")
    LogMessage("CT detection result: " ctResult)
    
    if InStr(ctResult, "CT_DETECTION_RESULT=1") {
        ; Extract CT coordinates
        if RegExMatch(ctResult, "CT_ROW_X=(\d+)", &ctXMatch) {
            ctBaseX := Integer(ctXMatch[1])
            
            if RegExMatch(ctResult, "CT_ROW_Y=(\d+)", &ctYMatch) {
                ctBaseY := Integer(ctYMatch[1])
                ctFound := true
                LogMessage("Found CT first player row at " ctBaseX "," ctBaseY)
            }
        }
    } else {
        LogMessage("Failed to detect CT team position")
    }
    
    ; ---- STEP 3: Find T team base position using same screenshot ----
    LogMessage("Finding T team base position...")
    tResult := RunPythonDetector("t")
    LogMessage("T detection result: " tResult)
    
    if InStr(tResult, "T_DETECTION_RESULT=1") {
        ; Extract T coordinates
        if RegExMatch(tResult, "T_ROW_X=(\d+)", &tXMatch) {
            tBaseX := Integer(tXMatch[1])
            
            if RegExMatch(tResult, "T_ROW_Y=(\d+)", &tYMatch) {
                tBaseY := Integer(tYMatch[1])
                tFound := true
                LogMessage("Found T first player row at " tBaseX "," tBaseY)
            }
        }
    } else {
        LogMessage("Failed to detect T team position")
    }
    
    ; ---- STEP 4: Pre-process all player coordinates first ----
    ; We'll first extract all nicknames from the single screenshot, then process profiles separately
    
    ; Process CT player coordinates and nicknames
    ctNicknames := []
    if (ctFound) {
        LogMessage("Extracting CT player nicknames...")
        
        Loop maxPlayersToCheck {
            playerIndex := A_Index - 1
            currentY := ctBaseY + (playerIndex * playerRowHeight)
            
            ; We're using the SAME screenshot for all nickname extraction
            ctNicknameResult := RunPythonDetector("nickname_ct " ctBaseX " " currentY)
            
            if InStr(ctNicknameResult, "CT_NICKNAME_RESULT=1") {
                if RegExMatch(ctNicknameResult, "CT_NICKNAME=([^\r\n]+)", &ctMatch) {
                    nickname := Trim(ctMatch[1])
                    
                    if (StrLen(nickname) > 0) {
                        LogMessage("Found CT player " (playerIndex + 1) " nickname: " nickname)
                        ctNicknames.Push({
                            index: playerIndex,
                            nickname: nickname,
                            x: ctBaseX,
                            y: currentY
                        })
                    } else {
                        LogMessage("Empty nickname detected for CT position " (playerIndex + 1) " - stopping CT scan")
                        break
                    }
                } else {
                    LogMessage("No nickname found for CT position " (playerIndex + 1) " - stopping CT scan")
                    break
                }
            } else {
                LogMessage("Failed to detect nickname for CT position " (playerIndex + 1) " - stopping CT scan")
                break
            }
        }
        LogMessage("Extracted " ctNicknames.Length " CT player nicknames")
    }
    
    ; Process T player coordinates and nicknames
    tNicknames := []
    if (tFound) {
        LogMessage("Extracting T player nicknames...")
        
        Loop maxPlayersToCheck {
            playerIndex := A_Index - 1
            currentY := tBaseY + (playerIndex * playerRowHeight)
            
            ; We're using the SAME screenshot for all nickname extraction
            tNicknameResult := RunPythonDetector("nickname_t " tBaseX " " currentY)
            
            if InStr(tNicknameResult, "T_NICKNAME_RESULT=1") {
                if RegExMatch(tNicknameResult, "T_NICKNAME=([^\r\n]+)", &tMatch) {
                    nickname := Trim(tMatch[1])
                    
                    if (StrLen(nickname) > 0) {
                        LogMessage("Found T player " (playerIndex + 1) " nickname: " nickname)
                        tNicknames.Push({
                            index: playerIndex,
                            nickname: nickname,
                            x: tBaseX,
                            y: currentY
                        })
                    } else {
                        LogMessage("Empty nickname detected for T position " (playerIndex + 1) " - stopping T scan")
                        break
                    }
                } else {
                    LogMessage("No nickname found for T position " (playerIndex + 1) " - stopping T scan")
                    break
                }
            } else {
                LogMessage("Failed to detect nickname for T position " (playerIndex + 1) " - stopping T scan")
                break
            }
        }
        LogMessage("Extracted " tNicknames.Length " T player nicknames")
    }
    
    ; ---- STEP 5: NOW process player profiles with separate screenshots ----
    
    ; Process CT player profiles
    for i, player in ctNicknames {
        LogMessage("Processing CT player profile: " player.nickname)
        
        ; Click to view player profile
        Click player.x + 10, player.y + 10
        Sleep 2000
        
        ; Take screenshot of profile
        CaptureScreenshot()
        Sleep 1000
        
        ; Click again to exit profile view
        Click player.x + 10, player.y + 10
        Sleep 1000
        
        ; Add to final player list
        ctPlayers.Push(player)
    }
    
    ; Process T player profiles
    for i, player in tNicknames {
        LogMessage("Processing T player profile: " player.nickname)
        
        ; Click to view player profile
        Click player.x + 10, player.y + 10
        Sleep 2000
        
        ; Take screenshot of profile
        CaptureScreenshot()
        Sleep 1000
        
        ; Click again to exit profile view
        Click player.x + 10, player.y + 10
        Sleep 1000
        
        ; Add to final player list
        tPlayers.Push(player)
    }
    
    ; Log summary
    LogMessage("Player processing summary:")
    LogMessage("- CT Players: " ctPlayers.Length)
    for i, player in ctPlayers
        LogMessage("  [" i "] " player.nickname)
    
    LogMessage("- T Players: " tPlayers.Length)
    for i, player in tPlayers
        LogMessage("  [" i "] " player.nickname)
    
    return (ctPlayers.Length > 0 || tPlayers.Length > 0)
}

ProcessMatch() {
    LogMessage("Processing match...")
    
    ; Wait a few seconds for the match to fully load
    Sleep 500
    
    ; View the player list using Tab
    ViewPlayerList()
    
    ; Process all players from both teams
    ProcessAllPlayers()
    
    ; Return to main menu using ESC
    ReturnToMainMenu()
    
    LogMessage("Match processing completed")
    return true
}

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
    Sleep 1000
    
    ; Take screenshot of player list
    LogMessage("Taking screenshot of player list...")
    CaptureScreenshot()
    
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
    Sleep 500
    
    ; Take screenshot to confirm we're back at the main menu
    CaptureScreenshot()
    
    ; Wait a bit longer for the main menu to fully load
    Sleep 1000
    
    return true
}