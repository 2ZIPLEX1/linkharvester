; CS2 Automation - Refactored In-Game Module
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
    
    LogMessage("Using a single screenshot for all player detection")
    
    ; ---- STEP 2: Find team positions using saved screenshot ----
    ctFound := FindTeamPosition("ct", &ctBaseX, &ctBaseY)
    tFound := FindTeamPosition("t", &tBaseX, &tBaseY)
    
    ; ---- STEP 3: Extract player nicknames ----
    ctNicknames := ExtractPlayerNicknames("CT", ctFound, ctBaseX, ctBaseY, playerRowHeight, maxPlayersToCheck)
    tNicknames := ExtractPlayerNicknames("T", tFound, tBaseX, tBaseY, playerRowHeight, maxPlayersToCheck)
    
    ; ---- STEP 4: Process player profiles ----
    ; Process CT player profiles
    for i, player in ctNicknames {
        ProcessPlayerProfile("CT", player, &ctPlayers)
    }

    ; Process T player profiles
    for i, player in tNicknames {
        ProcessPlayerProfile("T", player, &tPlayers)
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

; Find the base position for a team (CT or T)
FindTeamPosition(team, &baseX, &baseY) {
    LogMessage("Finding " team " team base position...")
    result := RunPythonDetector(team)
    LogMessage(team " detection result: " result)
    
    ; Convert team to uppercase for matching
    upperTeam := Format("{:U}", team)
    
    if InStr(result, upperTeam "_DETECTION_RESULT=1") {
        ; Extract coordinates
        if RegExMatch(result, upperTeam "_ROW_X=(\d+)", &xMatch) {
            baseX := Integer(xMatch[1])
            
            if RegExMatch(result, upperTeam "_ROW_Y=(\d+)", &yMatch) {
                baseY := Integer(yMatch[1])
                LogMessage("Found " team " first player row at " baseX "," baseY)
                return true
            }
        }
    } 
    
    LogMessage("Failed to detect " team " team position")
    return false
}

; Extract player nicknames for a team
ExtractPlayerNicknames(team, teamFound, baseX, baseY, rowHeight, maxPlayers) {
    nicknames := []
    
    if (!teamFound) {
        return nicknames
    }
    
    LogMessage("Extracting " team " player nicknames...")
    
    ; Convert team to uppercase for matching
    upperTeam := Format("{:U}", team)
    
    Loop maxPlayers {
        playerIndex := A_Index - 1
        currentY := baseY + (playerIndex * rowHeight)
        
        ; Using the SAME screenshot for all nickname extraction
        nicknameResult := RunPythonDetector("nickname_" team " " baseX " " currentY)
        
        if InStr(nicknameResult, upperTeam "_NICKNAME_RESULT=1") {
            if RegExMatch(nicknameResult, upperTeam "_NICKNAME=([^\r\n]+)", &match) {
                nickname := Trim(match[1])
                
                ; Clean and validate nickname
                nickname := CleanPlayerNickname(nickname, team)
                
                if (StrLen(nickname) > 0) {
                    ; Skip bots (nicknames starting with "BOT ")
                    if (SubStr(nickname, 1, 4) = "BOT ") {
                        LogMessage("Skipping " team " bot player: " nickname)
                        continue
                    }
                    
                    LogMessage("Found " team " player " (playerIndex + 1) " nickname: " nickname)
                    nicknames.Push({
                        index: playerIndex,
                        nickname: nickname,
                        x: baseX,
                        y: currentY
                    })
                } else {
                    LogMessage("Empty nickname detected for " team " position " (playerIndex + 1) " - stopping scan")
                    break
                }
            } else {
                LogMessage("No nickname found for " team " position " (playerIndex + 1) " - stopping scan")
                break
            }
        } else {
            LogMessage("Failed to detect nickname for " team " position " (playerIndex + 1) " - stopping scan")
            break
        }
    }
    
    LogMessage("Extracted " nicknames.Length " " team " player nicknames")
    return nicknames
}

; Clean player nickname by removing known patterns and special characters
CleanPlayerNickname(nickname, team) {
    ; First, handle known icon patterns
    knownPatterns := ["@", "@&", "@�", "�", "�", "&"]
    for pattern in knownPatterns {
        if (SubStr(nickname, 1, StrLen(pattern)) = pattern) {
            nickname := Trim(SubStr(nickname, StrLen(pattern) + 1))
            LogMessage("Removed icon pattern '" pattern "' from " team " nickname")
            break
        }
    }
    
    ; Then, remove any remaining non-alphanumeric characters at the beginning
    while (StrLen(nickname) > 0) {
        firstChar := SubStr(nickname, 1, 1)
        if (RegExMatch(firstChar, "[A-Za-z0-9\[\]_]"))
            break
        nickname := Trim(SubStr(nickname, 2))
        LogMessage("Removed leading character '" firstChar "' from " team " nickname")
    }
    
    return nickname
}

; Process an individual player's profile
ProcessPlayerProfile(team, player, &playersArray) {
    LogMessage("Processing " team " player profile: " player.nickname)
    
    ; Calculate exact click coordinates
    clickX := player.x + 10
    clickY := player.y + 10
    LogMessage("Clicking " team " player at coordinates: " clickX "," clickY)
    
    ; First, view the player's in-game profile
    ViewPlayerInGameProfile(clickX, clickY)
    
    ; Then, access their Steam profile
    steamUrl := AccessSteamProfile(clickX, clickY, player.nickname)
    
    ; Save the Steam profile URL if we got one
    if (steamUrl) {
        player.steamUrl := steamUrl
    }
    
    ; Click again to exit profile view
    Click clickX, clickY
    Sleep 500
    
    ; Add to final player list
    playersArray.Push(player)
}

; View a player's in-game profile
ViewPlayerInGameProfile(clickX, clickY) {
    ; Click to view player profile
    Click clickX, clickY
    Sleep 1000
    
    ; Take screenshot of profile
    CaptureScreenshot()
    Sleep 1000
    
    return true
}

; Access and extract the Steam profile URL for a player
AccessSteamProfile(clickX, clickY, nickname := "") {
    try {
        ; Calculate position of the profile button (offset from player click)
        profileButtonX := clickX + 80
        profileButtonY := clickY + 150
        LogMessage("Clicking profile button at: " profileButtonX "," profileButtonY)
        
        ; Click the profile button
        Click profileButtonX, profileButtonY
        Sleep 3000  ; Give Steam browser time to open
        
        ; Click the address bar
        addressBarX := 511
        addressBarY := 177
        LogMessage("Clicking address bar at: " addressBarX "," addressBarY)
        Click addressBarX, addressBarY
        Sleep 1000
        ; Select all and copy URL
        Send("^a")  ; Ctrl+A to select all
        Sleep(1000)
        Send("^c")  ; Ctrl+C to copy
        Sleep(1000)
        CaptureScreenshot()

        ; Retrieve the URL from clipboard
        steamProfileUrl := A_Clipboard
        LogMessage("Retrieved Steam profile URL: " steamProfileUrl)
        
        ; Save URL to file if we have a nickname
        if (nickname)
            SaveProfileUrl(nickname, steamProfileUrl)
        
        ; Close the Steam browser (Escape)
        Send "{Escape}"
        Sleep 500
        
        return steamProfileUrl
    } catch Error as e {
        LogMessage("Error accessing Steam profile: " e.Message)
        ; Try to close Steam browser if it's open
        Send "{Escape}"
        Sleep 500
        return ""
    }
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