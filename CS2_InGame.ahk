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

; Update ProcessPlayerProfile to use the new medal criteria
ProcessPlayerProfile(team, player, &playersArray) {
    LogMessage("Processing " team " player profile: " player.nickname)
    
    ; Calculate exact click coordinates
    clickX := player.x + 10
    clickY := player.y + 10
    LogMessage("Clicking " team " player at coordinates: " clickX "," clickY)
    
    ; First, view the player's in-game profile
    ViewPlayerInGameProfile(clickX, clickY)
    
    ; Check for medals using the improved function
    medalInfo := CheckPlayerMedals(clickX, clickY)
    
    ; Log medal information
    LogMessage("Medal detection results: Has 4+ medals: " (medalInfo.hasFourMedals ? "Yes" : "No") 
              ", Has 5-year coin: " (medalInfo.hasFiveYearCoin ? "Yes" : "No")
              ", Total medals: " medalInfo.medalCount
              ", Meets criteria: " (medalInfo.meetsAllCriteria ? "Yes" : "No"))
    
    ; If the player doesn't meet our criteria, skip further processing
    if (!medalInfo.meetsAllCriteria) {
        LogMessage("Player doesn't meet medal criteria, skipping profile")
        
        ; Close the profile view
        Click clickX, clickY
        Sleep 500
        
        ; Don't add to player array
        return false
    }
    
    ; Store medal information
    player.medals := medalInfo.medals
    player.medalCount := medalInfo.medalCount
    player.hasMoreMedals := medalInfo.hasMoreMedals
    
    ; Then, access their Steam profile
    steamUrl := AccessSteamProfile(clickX, clickY, player.nickname)
    
    ; Save the Steam profile URL if we got one
    if (steamUrl) {
        player.steamUrl := steamUrl
    }
    
    ; Close the profile view
    Click clickX, clickY
    Sleep 500
    
    ; Add to final player list
    playersArray.Push(player)
    return true
}

; Helper function to convert array to text for logging
AsText(array) {
    result := "["
    for i, element in array {
        if (i > 1)
            result .= ", "
        result .= element
    }
    result .= "]"
    return result
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

; Access and extract the Steam profile URL for a player using OCR
AccessSteamProfile(clickX, clickY, nickname := "") {
    try {
        ; Calculate position of the profile button (offset from player click)
        profileButtonX := clickX + 80
        profileButtonY := clickY + 150
        LogMessage("Clicking profile button at: " profileButtonX "," profileButtonY)
        
        ; Click the profile button
        Click profileButtonX, profileButtonY
        Sleep 3000  ; Give Steam browser time to open
        
        ; Take screenshot of the browser for OCR recognition
        LogMessage("Taking screenshot for URL OCR recognition")
        CaptureScreenshot()
        Sleep 1500  ; Give enough time for the screenshot to be saved
        
        ; Run Python URL extractor
        LogMessage("Running URL OCR extraction")
        urlResult := RunPythonDetector("extract_url")
        LogMessage("URL extraction result: " urlResult)
        
        ; Parse the OCR output to get the URL
        steamProfileUrl := ""
        if InStr(urlResult, "URL_EXTRACTION_RESULT=1") {
            ; Try to extract the URL from the output
            if RegExMatch(urlResult, "URL=([^\r\n]+)", &match) {
                steamProfileUrl := Trim(match[1])
                LogMessage("Extracted Steam profile URL via OCR: " steamProfileUrl)
            }
        } else {
            ; Extract error message if available
            errorMsg := "Unknown error"
            if RegExMatch(urlResult, "URL_EXTRACTION_ERROR=([^\r\n]+)", &match)
                errorMsg := Trim(match[1])
            LogMessage("Failed to extract URL: " errorMsg)
        }
        
        ; Save URL to file if we have a nickname and URL
        if (nickname && steamProfileUrl)
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

; Process players by clicking through a grid pattern with unified profile analysis
ProcessPlayersGridMethod() {
    LogMessage("Processing players using grid method with unified profile analysis...")
    
    ; Constants for grid scanning
    startX := 720       ; X coordinate to start scanning
    startY := 300       ; Y coordinate to start scanning
    endY := 820         ; Y coordinate to stop scanning
    rowHeight := 26     ; Vertical distance between rows
    
    ; Counter for profiles found
    profilesFound := 0
    
    ; Make sure the scoreboard is visible
    EnsureScoreboardVisible()
    
    ; Iterate through the grid pattern
    currentY := startY
    while (currentY <= endY) {
        LogMessage("Checking row at y-coordinate: " currentY)
        
        ; Click at the current position
        Click startX, currentY
        Sleep 1000  ; Wait for any profile window to appear
        
        ; Take a screenshot to check if profile details loaded
        CaptureScreenshot()
        Sleep 1000  ; Wait for screenshot to be saved
        
        ; Perform unified profile analysis with a single Python call
        LogMessage("Performing unified profile analysis...")
        analysisResult := RunPythonDetector("analyze_profile " startX " " currentY)
        LogMessage("Profile analysis result: " analysisResult)
        
        ; Parse the analysis results
        profileButtonFound := InStr(analysisResult, "PROFILE_BUTTON_FOUND=1")
        meetsCriteria := InStr(analysisResult, "MEETS_CRITERIA=1")
        decision := ""
        
        ; Extract the decision
        if RegExMatch(analysisResult, "DECISION=([A-Z]+)", &match)
            decision := match[1]
        
        ; Extract profile button coordinates if found
        profileButtonX := 0
        profileButtonY := 0
        if (profileButtonFound && RegExMatch(analysisResult, "PROFILE_BUTTON_COORDS=(\d+),(\d+)", &coordMatch)) {
            profileButtonX := Integer(coordMatch[1])
            profileButtonY := Integer(coordMatch[2])
            LogMessage("Profile button found at coordinates: " profileButtonX "," profileButtonY)
        }
        
        ; Extract medal information for logging
        medalCount := 0
        has5YearCoin := false
        hasMoreMedals := false
        detectedMedals := []
        
        if RegExMatch(analysisResult, "MEDAL_COUNT=(\d+)", &countMatch)
            medalCount := Integer(countMatch[1])
            
        has5YearCoin := InStr(analysisResult, "HAS_5YEAR_COIN=1")
        hasMoreMedals := InStr(analysisResult, "HAS_MORE_MEDALS=1")
        
        ; Parse individual medals
        fileContent := analysisResult
        Loop Parse, fileContent, "`n", "`r" {
            if InStr(A_LoopField, "MEDAL_DETECTED=") {
                if RegExMatch(A_LoopField, "MEDAL_DETECTED=([^`r`n]+)", &medalMatch) {
                    medalName := Trim(medalMatch[1])
                    detectedMedals.Push(medalName)
                }
            }
        }
        
        ; Log comprehensive analysis results
        LogMessage("Analysis summary:")
        LogMessage("- Profile button found: " (profileButtonFound ? "Yes" : "No"))
        LogMessage("- Medal count: " medalCount)
        LogMessage("- Has 5-year veteran coin: " (has5YearCoin ? "Yes" : "No"))
        LogMessage("- Has more medals indicator: " (hasMoreMedals ? "Yes" : "No"))
        LogMessage("- Meets all criteria: " (meetsCriteria ? "Yes" : "No"))
        LogMessage("- Decision: " decision)
        
        ; Generate a list of medals for logging
        if (detectedMedals.Length > 0) {
            medalList := ""
            for i, medal in detectedMedals
                medalList .= medal ", "
            LogMessage("- Detected medals: " medalList)
        }
        
        ; Process based on decision
        if (decision = "PROCEED" && profileButtonFound) {
            LogMessage("Player meets criteria, proceeding to view Steam profile")
            
            ; Click the profile button at its exact detected coordinates
            LogMessage("Clicking profile button at exact coordinates: " profileButtonX "," profileButtonY)
            Click profileButtonX, profileButtonY
            Sleep 3000  ; Give Steam browser time to open
            
            ; Take screenshot for URL OCR
            CaptureScreenshot()
            Sleep 1500  ; Give enough time for screenshot to be saved
            
            ; Extract Steam profile URL
            steamProfileUrl := ExtractSteamProfileUrl()
            
            ; If we got a URL, save it
            if (steamProfileUrl) {
                LogMessage("Found Steam profile URL: " steamProfileUrl)
                
                ; Create player identifier based on medal info
                playerIdentifier := "player_medals" medalCount "_5yrcoin" (has5YearCoin ? "Yes" : "No")
                
                ; Save profile URL with medal information
                SaveProfileUrl(playerIdentifier, steamProfileUrl)
                profilesFound++
            }
            
            ; Close the Steam browser window AND profile details with Escape
            LogMessage("Closing Steam browser window and profile details...")
            Send "{Escape}"
            Sleep 1000
            Send "{Escape}"
            Sleep 500
        } else {
            LogMessage("Player doesn't meet criteria or no profile button found, skipping profile")
            
            ; Just click again at the same coordinates to close profile details
            LogMessage("Clicking again to close profile details")
            Click startX, currentY
            Sleep 500
        }
        
        ; Move to the next row
        currentY += rowHeight
    }
    
    LogMessage("Grid scanning completed. Found " profilesFound " qualified player profiles.")
    
    ; Return to normal game view
    Send "{Escape}"  ; Close the scoreboard
    Sleep 500
    
    return profilesFound > 0
}

; Function to find the exact coordinates of the profile button
FindProfileButton(clickX, clickY, &outX, &outY) {
    LogMessage("Searching for exact profile button coordinates around " clickX "," clickY)
    
    ; Define the search region (expanded area around click position)
    regionX := clickX + 60  ; Start from 70px to the right of click
    regionY := clickY + 35  ; Start from 75px above click
    regionWidth := 30      ; Width to cover the expanded area
    regionHeight := 155     ; Height to cover the expanded area
    
    ; Run profile button detection using Python
    result := RunPythonDetector("profile_button " regionX " " regionY " " regionWidth " " regionHeight)
    LogMessage("Profile button detection result: " result)
    
    ; Check if the button was detected
    if InStr(result, "PROFILE_BUTTON_RESULT=1") {
        ; Extract the exact coordinates
        if RegExMatch(result, "PROFILE_BUTTON_COORDS=(\d+),(\d+)", &match) {
            outX := Integer(match[1])
            outY := Integer(match[2])
            LogMessage("Found profile button at exact coordinates: " outX "," outY)
            return true
        } else {
            LogMessage("Profile button detected but couldn't extract coordinates")
            return false
        }
    }
    
    LogMessage("No profile button detected in search region")
    return false
}

; Function to ensure the scoreboard is visible
EnsureScoreboardVisible() {
    LogMessage("Ensuring scoreboard is visible...")
    
    ; Make sure CS2 is the active window
    if !WinActive("Counter-Strike") {
        LogMessage("CS2 not active, activating now...")
        WinActivate "Counter-Strike"
        Sleep 1000
    }
    
    ; Press Escape to open the pause menu/scoreboard
    LogMessage("Pressing Escape to view scoreboard...")
    Send "{Escape}"
    Sleep 1000
    
    LogMessage("Scoreboard should now be visible.")
    return true
}

; Function to check if the profile button is visible using template matching
IsProfileButtonVisible(x, y) {
    LogMessage("Checking for profile button with expanded ROI")
    
    ; Define the larger region to check (expanded as specified)
    regionX := x - 70  ; Start from 70px to the left of provided x
    regionY := y - 75  ; Start from 75px above provided y
    regionWidth := 180 ; Width to cover from (x-70) to (x+110)
    regionHeight := 295 ; Height to cover from (y-75) to (y+220)
    
    ; Run profile button detection using Python
    result := RunPythonDetector("profile_button " regionX " " regionY " " regionWidth " " regionHeight)
    LogMessage("Profile button detection result: " result)
    
    ; Check if the button was detected
    if InStr(result, "PROFILE_BUTTON_RESULT=1") {
        LogMessage("Profile button detected in expanded ROI!")
        return true
    }
    
    LogMessage("No profile button detected in expanded ROI.")
    return false
}


; Function to check player medals using template matching in a single ROI
CheckPlayerMedals(clickX, clickY) {
    LogMessage("Analyzing player medals in a single ROI relative to click position " clickX "," clickY)
    
    ; Define a single, larger ROI that covers all medal slots
    ; Starting at offset 28,-150 with size 384x413
    roiX := clickX + 28
    roiY := clickY - 150
    roiWidth := 384
    roiHeight := 413
    
    ; Take a screenshot for analysis
    CaptureScreenshot()
    Sleep 1000  ; Wait for screenshot to be saved
    
    ; Run medal detection using Python
    medalDetectionResult := RunPythonDetector("detect_medals " roiX " " roiY " " roiWidth " " roiHeight)
    LogMessage("Medal detection result: " medalDetectionResult)
    
    ; Parse the medal detection results
    detectedMedals := []
    hasFiveYearCoin := false
    totalMedals := 0
    
    ; Process detection result to count medals and check for 5-year veteran coin
    Loop Parse, medalDetectionResult, "`n", "`r" {
        LogMessage("Parsing line: " A_LoopField)
        
        ; Check for total medal count
        if RegExMatch(A_LoopField, "MEDAL_COUNT=(\d+)", &countMatch) {
            totalMedals := Integer(countMatch[1])
            LogMessage("Total medals detected: " totalMedals)
        }
        
        ; Check for veteran coin specifically
        if InStr(A_LoopField, "MEDAL_DETECTED=5-year-veteran-coin") {
            hasFiveYearCoin := true
            LogMessage("5-year veteran coin detected")
        }
        
        ; Add all detected medals to the list
        if RegExMatch(A_LoopField, "MEDAL_DETECTED=([^`r`n]+)", &medalMatch) {
            medalName := Trim(medalMatch[1])
            detectedMedals.Push(medalName)
            LogMessage("Detected medal: " medalName)
        }
    }
    
    ; Check if there are more medals (look for arrow)
    hasMoreMedals := false
    if (totalMedals > 0) {
        arrowResult := RunPythonDetector("detect_medal_arrow")
        LogMessage("Medal arrow detection result: " arrowResult)
        hasMoreMedals := InStr(arrowResult, "MEDAL_ARROW_PRESENT=1")
    }
    
    ; Check if we meet our criteria:
    ; 1. Has 5-year veteran coin
    ; 2. Has at least 4 medals total
    hasSufficientMedals := (totalMedals >= 4)
    meetsAllCriteria := (hasFiveYearCoin && hasSufficientMedals)
    
    LogMessage("Medal analysis summary:")
    LogMessage("- Total medals detected: " totalMedals)
    LogMessage("- Has 5-year veteran coin: " (hasFiveYearCoin ? "Yes" : "No"))
    LogMessage("- Has sufficient medals (4+): " (hasSufficientMedals ? "Yes" : "No"))
    LogMessage("- Has more medals indicator: " (hasMoreMedals ? "Yes" : "No"))
    LogMessage("- Meets all criteria: " (meetsAllCriteria ? "Yes" : "No"))
    
    ; Return the medal information
    return {
        hasFourMedals: hasSufficientMedals,
        hasFiveYearCoin: hasFiveYearCoin,
        meetsAllCriteria: meetsAllCriteria,
        medals: detectedMedals,
        medalCount: totalMedals,
        hasMoreMedals: hasMoreMedals
    }
}

; Function to extract Steam profile URL using OCR
ExtractSteamProfileUrl() {
    LogMessage("Extracting Steam profile URL using OCR...")
    
    ; Run the URL extraction
    urlResult := RunPythonDetector("extract_url")
    LogMessage("URL extraction result: " urlResult)
    
    ; Parse the OCR output to get the URL
    steamProfileUrl := ""
    if InStr(urlResult, "URL_EXTRACTION_RESULT=1") {
        ; Try to extract the URL from the output
        if RegExMatch(urlResult, "URL=([^\r\n]+)", &match) {
            steamProfileUrl := Trim(match[1])
            LogMessage("Successfully extracted Steam profile URL: " steamProfileUrl)
            return steamProfileUrl
        }
    } else {
        ; Extract error message if available
        errorMsg := "Unknown error"
        if RegExMatch(urlResult, "URL_EXTRACTION_ERROR=([^\r\n]+)", &match)
            errorMsg := Trim(match[1])
        LogMessage("Failed to extract URL: " errorMsg)
    }
    
    return ""
}

; Replace or modify the ProcessMatch function to use the new grid method
ProcessMatch() {
    LogMessage("Processing match...")
    
    ; Wait a few seconds for the match to fully load
    Sleep 500
    
    ; Process players using the simplified grid method
    success := ProcessPlayersGridMethod()
    
    ; Return to main menu using ESC
    ReturnToMainMenu()
    
    if (success) {
        LogMessage("Match processing completed successfully")
        return true
    } else {
        LogMessage("Match processing completed but no profiles were found")
        return false
    }
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

