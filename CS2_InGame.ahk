; CS2 Automation - Refactored In-Game Module
; Handles actions once a match has been successfully joined

#Include "CS2_API_Integration.ahk"

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

; Helper function to close Steam browser tabs and overlay
CloseTabAndOverlay(urlResult) {
    ; Check if tab close button was found
    tabCloseX := 0
    tabCloseY := 0
    tabCloseFound := false
    
    if InStr(urlResult, "TAB_CLOSE_BUTTON_FOUND=1") {
        if RegExMatch(urlResult, "TAB_CLOSE_COORDS=(\d+),(\d+)", &coordMatch) {
            tabCloseX := Integer(coordMatch[1])
            tabCloseY := Integer(coordMatch[2])
            tabCloseFound := true
            LogMessage("Tab close button found at: " tabCloseX "," tabCloseY)
        }
    }
    
    ; Close the tabs and overlay using clicks
    if (tabCloseFound) {
        ; First click the tab close button (adjusted X to target the 'x' specifically)
        LogMessage("Clicking tab close button at: " tabCloseX-13 "," tabCloseY)
        Click tabCloseX-13, tabCloseY
        Sleep 1000  ; Wait for tab to close
        
        ; Then click the overlay close button
        overlayCloseX := 1874
        overlayCloseY := 48
        LogMessage("Clicking overlay close button at: " overlayCloseX "," overlayCloseY)
        Click overlayCloseX, overlayCloseY
        Sleep 1000  ; Wait for overlay to close
        
        return true
    } else {
        ; Fallback to Escape key if tab close button not found
        LogMessage("Tab close button not found, using Escape key as fallback")
        Send "{Escape}"
        Sleep 1000
        
        return false
    }
}

; Modified version of ExtractSteamProfileUrl to integrate with API
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
            
            ; NEW: Use the API-integrated function instead of calling AddToSteamProfileQueue
            playerIdentifier := "player_medals_5yrcoin"
            SaveProfileUrlWithAPI(playerIdentifier, steamProfileUrl)
            
            ; Close the tab and overlay
            CloseTabAndOverlay(urlResult)
            
            return steamProfileUrl
        }
    } else {
        ; Extract error message if available
        errorMsg := "Unknown error"
        if RegExMatch(urlResult, "URL_EXTRACTION_ERROR=([^\r\n]+)", &match)
            errorMsg := Trim(match[1])
        LogMessage("Failed to extract URL: " errorMsg)
    }
    
    ; If we reached here, we didn't find a URL or couldn't close the tab
    ; Fallback to Escape key
    LogMessage("Using Escape key as fallback to close overlay")
    Send "{Escape}"
    Sleep 1000
    
    return ""
}

; Function to add URL to Steam profile queue
AddToSteamProfileQueue(url) {
    try {
        LogMessage("Adding URL to Steam profile queue: " . url)
        
        ; Use Chr(34) for quote characters to avoid complex nesting
        quote := Chr(34)
        command := A_ComSpec . " /c python steam_bridge.py add " . quote . url . quote
        
        ; Use RunWait for AHK v2
        shell := ComObject("WScript.Shell")
        exec := shell.Exec(command)
        result := exec.StdOut.ReadAll()
        
        ; Log the result
        LogMessage("Queue result: " . result)
        
        return true
    } catch Error as e {
        LogMessage("Error adding URL to queue: " . e.Message)
        return false
    }
}

; Corrected ProcessPlayersGridMethod function with optimized checks
ProcessPlayersGridMethod() {
    LogMessage("Processing players using grid method with structured profile analysis...")
    
    ; Default constants for grid scanning
    defaultStartX := 720       ; X coordinate to start scanning
    defaultStartY := 326       ; Default Y coordinate to start scanning (fallback)
    endY := 836                ; Y coordinate to stop scanning
    rowHeight := 26            ; Vertical distance between rows
    
    ; Counter for profiles found
    profilesFound := 0
    
    ; Ensure the scoreboard is visible and get the icon's Y position
    iconStartY := 0
    if (!EnsureScoreboardVisible(&iconStartY)) {
        LogMessage("Failed to ensure scoreboard is visible. Exiting.")
        return false
    }
    
    ; Calculate optimal starting Y position based on icon's Y position
    startY := (iconStartY > 0) ? (iconStartY + 65) : defaultStartY
    startX := defaultStartX
    
    LogMessage("Using icon-based starting position: X=" startX ", Y=" startY " (icon found at Y=" iconStartY ")")
    
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
        
        ; Perform initial profile analysis (includes profile button, sympathies, and medals check)
        LogMessage("Performing profile analysis...")
        analysisResult := RunPythonDetector("analyze_profile " startX " " currentY)
        LogMessage("Profile analysis result: " analysisResult)
        
        ; Parse the initial analysis results
        profile_button_found := InStr(analysisResult, "PROFILE_BUTTON_FOUND=1")
        three_plus_medals_found := InStr(analysisResult, "THREE_PLUS_MEDALS_FOUND=1")
        five_year_medal_found := InStr(analysisResult, "FIVE_YEAR_MEDAL_FOUND=1")
        unwanted_medals_found := InStr(analysisResult, "UNWANTED_MEDALS_FOUND=1")
        more_medals_available := InStr(analysisResult, "CLICK_TO_SEE_MORE_MEDALS=1")
        too_many_sympathies := InStr(analysisResult, "TOO_MANY_SYMPATHIES=1")
        
        ; Extract sympathies sum for logging
        sympathies_sum := 0
        if RegExMatch(analysisResult, "SYMPATHIES_SUM=(\d+)", &sumMatch)
            sympathies_sum := Integer(sumMatch[1])
        
        ; Extract medal count for logging
        medalCount := 0
        if RegExMatch(analysisResult, "MEDAL_COUNT=(\d+)", &countMatch)
            medalCount := Integer(countMatch[1])
        
        ; Extract profile button coordinates if found
        profileButtonX := 0
        profileButtonY := 0
        if (profile_button_found && RegExMatch(analysisResult, "PROFILE_BUTTON_COORDS=(\d+),(\d+)", &coordMatch)) {
            profileButtonX := Integer(coordMatch[1])
            profileButtonY := Integer(coordMatch[2])
            LogMessage("Profile button found at coordinates: " profileButtonX "," profileButtonY)
        }
        
        ; Log comprehensive analysis results
        LogMessage("Initial analysis summary:")
        LogMessage("- Profile button found: " (profile_button_found ? "Yes" : "No"))
        if (profile_button_found) {
            LogMessage("- Sympathies sum: " sympathies_sum)
            LogMessage("- Too many sympathies: " (too_many_sympathies ? "Yes" : "No"))
            LogMessage("- Three+ medals found: " (three_plus_medals_found ? "Yes" : "No"))
            LogMessage("- 5-year veteran coin found: " (five_year_medal_found ? "Yes" : "No"))
            LogMessage("- Unwanted medals found: " (unwanted_medals_found ? "Yes" : "No"))
            LogMessage("- More medals available: " (more_medals_available ? "Yes" : "No"))
            LogMessage("- Medal count: " medalCount)
        }
        
        ; Make initial decision
        shouldContinue := true
        
        ; Early skip conditions (in optimized order)
        if (!profile_button_found) {
            LogMessage("No profile button found, skipping player")
            shouldContinue := false
        } else if (too_many_sympathies) {
            LogMessage("Player has too many sympathies (" sympathies_sum " > 100), skipping player")
            shouldContinue := false
        } else if (unwanted_medals_found) {
            LogMessage("Unwanted medals found, skipping player")
            shouldContinue := false
        } else if (!three_plus_medals_found) {
            LogMessage("Less than 4 medals found, skipping player")
            shouldContinue := false
        }
        
        ; If we should continue and more medals are available, click to see more medals
        maxArrowClicks := 3  ; Maximum number of times to click the arrow to prevent infinite loops
        arrowClickCount := 0
        
        ; If we need to continue and more medals are available, click on the arrow
        while (shouldContinue && more_medals_available && arrowClickCount < maxArrowClicks) {
            ; Default arrow coordinates (fallback if detection fails)
            arrowX := startX + 394
            arrowY := currentY - 35
            
            ; Try to get precise arrow coordinates from Python analysis
            foundArrowX := false
            foundArrowY := false
            
            ; Parse the output line by line to find the coordinates
            Loop Parse, analysisResult, "`n", "`r" {
                if (InStr(A_LoopField, "ARROW_COORDS_X=")) {
                    if (RegExMatch(A_LoopField, "ARROW_COORDS_X=(\d+)", &xMatch)) {
                        arrowX := Integer(xMatch[1])
                        foundArrowX := true
                    }
                }
                else if (InStr(A_LoopField, "ARROW_COORDS_Y=")) {
                    if (RegExMatch(A_LoopField, "ARROW_COORDS_Y=(\d+)", &yMatch)) {
                        arrowY := Integer(yMatch[1])
                        foundArrowY := true
                    }
                }
                ; Also try the combined format as a fallback
                else if (InStr(A_LoopField, "ARROW_COORDS=")) {
                    if (RegExMatch(A_LoopField, "ARROW_COORDS=(\d+),(\d+)", &coordsMatch)) {
                        arrowX := Integer(coordsMatch[1])
                        arrowY := Integer(coordsMatch[2])
                        foundArrowX := true
                        foundArrowY := true
                    }
                }
            }
            
            LogMessage("Clicking medal arrow at: " arrowX+5 "," arrowY+7)
            Click arrowX+5, arrowY+7
            Sleep 1000  ; Wait for UI to update
            
            ; Take a new screenshot after clicking the arrow
            CaptureScreenshot()
            Sleep 1000  ; Wait for screenshot to be saved
            
            ; Analyze again with the new screenshot
            LogMessage("Performing follow-up profile analysis after arrow click...")
            followUpResult := RunPythonDetector("analyze_profile " startX " " currentY)
            
            ; Update the state variables that might change
            if (!five_year_medal_found)
                five_year_medal_found := InStr(followUpResult, "FIVE_YEAR_MEDAL_FOUND=1")
                
            if (!unwanted_medals_found)
                unwanted_medals_found := InStr(followUpResult, "UNWANTED_MEDALS_FOUND=1")
                
            more_medals_available := InStr(followUpResult, "CLICK_TO_SEE_MORE_MEDALS=1")
            
            ; Update medal count for logging
            if RegExMatch(followUpResult, "MEDAL_COUNT=(\d+)", &countMatch)
                medalCount := Integer(countMatch[1])
                
            ; For the next iteration, we need the full new analysis result
            analysisResult := followUpResult
            
            ; Log updated state
            arrowClickCount++
            LogMessage("After arrow click " arrowClickCount ":")
            LogMessage("- 5-year veteran coin found: " (five_year_medal_found ? "Yes" : "No"))
            LogMessage("- Unwanted medals found: " (unwanted_medals_found ? "Yes" : "No"))
            LogMessage("- More medals available: " (more_medals_available ? "Yes" : "No"))
            LogMessage("- Medal count: " medalCount)
            
            ; Check if we should stop because of unwanted medals
            if (unwanted_medals_found) {
                LogMessage("Unwanted medals found after viewing more medals, skipping player")
                shouldContinue := false
                break
            }
        }
        
        ; Make final decision after seeing all medals
        if (shouldContinue) {
            ; Final check for 5-year medal
            if (five_year_medal_found) {
                LogMessage("Player meets all criteria, proceeding to view Steam profile")
                
                ; Click the profile button at its exact detected coordinates
                LogMessage("Clicking profile button at exact coordinates: " profileButtonX "," profileButtonY)
                Click profileButtonX, profileButtonY
                Sleep 3000  ; Give Steam browser time to open
                
                ; Take screenshot for URL OCR
                CaptureScreenshot()
                Sleep 1500  ; Give enough time for screenshot to be saved
                
                ; Extract Steam profile URL
                steamProfileUrl := ExtractSteamProfileUrl()
            } else {
                LogMessage("Player has 4+ medals but no 5-year coin, skipping profile")
                
                ; Need to close profile details in this case
                LogMessage("Clicking again to close profile details")
                Click startX, currentY
                Sleep 500
            }
        } else {
            ; Only click to close profile details if we didn't open Steam profile
            LogMessage("Clicking again to close profile details")
            Click startX, currentY
            Sleep 500
        }
        
        ; Move to the next row
        currentY += rowHeight
    }
    
    LogMessage("Grid scanning completed. Found " profilesFound " qualified player profiles.")
    
    ; Return to normal game view
    ; Send "{Escape}"  ; Close the scoreboard
    ; Sleep 500
    
    return profilesFound > 0
}

; Function to ensure the scoreboard is visible
EnsureScoreboardVisible(&iconStartY := 0) {
    LogMessage("Ensuring scoreboard is visible...")
    
    ; Make sure CS2 is the active window
    if !WinActive("Counter-Strike") {
        LogMessage("CS2 not active, activating now...")
        WinActivate "Counter-Strike"
        Sleep 1000
    }
    
    ; Define ROI for scoreboard icon
    iconRoiX := 500
    iconRoiY := 225
    iconRoiWidth := 25
    iconRoiHeight := 180
    
    ; Try to show scoreboard up to 3 times
    Loop 3 {
        ; Press Escape to open the pause menu/scoreboard
        LogMessage("Pressing Escape to view scoreboard (attempt " A_Index "/3)...")
        Send "{Escape}"
        Sleep 2000  ; Wait 2 seconds for scoreboard to appear
        
        ; Take a screenshot
        CaptureScreenshot()
        Sleep 1000  ; Wait for screenshot to be saved
        
        ; Check if scoreboard is visible by looking for valve-cs2-icon.jpg
        LogMessage("Checking for scoreboard icon...")
        result := RunPythonDetector("check_scoreboard " iconRoiX " " iconRoiY " " iconRoiWidth " " iconRoiHeight)
        LogMessage("Scoreboard check result: " result)
        
        ; Check if icon was detected
        if InStr(result, "SCOREBOARD_VISIBLE=1") {
            ; Extract icon's Y position if available
            if RegExMatch(result, "ICON_Y=(\d+)", &yMatch) {
                iconStartY := Integer(yMatch[1])
                LogMessage("Scoreboard icon found at Y coordinate: " iconStartY)
                return true
            } else {
                ; Icon found but couldn't get Y position
                LogMessage("Scoreboard is visible but couldn't get icon Y position")
                iconStartY := iconRoiY  ; Use ROI start Y as fallback
                return true
            }
        }
        
        ; If we reach here, icon wasn't found on this attempt
        LogMessage("Scoreboard icon not found on attempt " A_Index "/3, trying again...")
        Sleep 1000  ; Wait before trying again
    }
    
    ; If we've tried 3 times and failed
    LogMessage("Failed to detect scoreboard after 3 attempts. Exiting.")
    MsgBox("Failed to detect CS2 scoreboard after 3 attempts.`n`nPlease check if the game is running correctly.", "Scoreboard Detection Error", "OK Icon!")
    return false
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
    Sleep 2500
    
    ; Take screenshot to confirm we're back at the main menu
    CaptureScreenshot()
    
    return true
}

