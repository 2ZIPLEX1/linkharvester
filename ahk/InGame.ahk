; CS2 Automation - Refactored In-Game Module
; Handles actions once a match has been successfully joined

#Include "Helpers.ahk"

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
    Sleep 500
    
    ; Take screenshot of profile
    CaptureScreenshot()
    ; Sleep 1000
    
    return true
}

; Helper function to close Steam browser tabs and overlay
CloseTabAndOverlay(urlResult) {
    ; Check if tab close button was found
    tabCloseX := 0
    tabCloseY := 0
    tabCloseFound := false
    isPreciseX := false
    
    if InStr(urlResult, "TAB_CLOSE_BUTTON_FOUND=1") {
        if RegExMatch(urlResult, "TAB_CLOSE_COORDS=(\d+),(\d+)", &coordMatch) {
            tabCloseX := Integer(coordMatch[1])
            tabCloseY := Integer(coordMatch[2])
            tabCloseFound := true
            LogMessage("Tab close button found at: " tabCloseX "," tabCloseY)
            
            ; Check if this is a precise X coordinate
            isPreciseX := InStr(urlResult, "PRECISE_X_FOUND=1")
            if (isPreciseX)
                LogMessage("Precise X button coordinates available - no offset needed")
        }
    }
    
    ; Close the tabs and overlay using clicks
    if (tabCloseFound) {
        ; Click the tab close button (with or without offset based on precision)
        if (isPreciseX) {
            ; Use exact coordinates for precise detection
            LogMessage("Clicking precise tab close button at: " tabCloseX "," tabCloseY)
            Sleep 300
            Click tabCloseX, tabCloseY
        } else {
            ; Use offset for x-plus based detection
            LogMessage("Clicking tab close button with offset at: " tabCloseX-13 "," tabCloseY)
            Click tabCloseX-13, tabCloseY
        }
        Sleep 500  ; Wait for tab to close
        
        ; Then click the overlay close button
        overlayCloseX := 1874
        overlayCloseY := 48
        LogMessage("Clicking overlay close button at: " overlayCloseX "," overlayCloseY)
        Click overlayCloseX, overlayCloseY
        Sleep 500  ; Wait for overlay to close
        
        return true
    } else {
        ; Fallback to Escape key if tab close button not found
        LogMessage("Tab close button not found, using Escape key as fallback")
        Send "{Escape}"
        Sleep 1000
        
        return false
    }
}

; Refactored version of ExtractSteamProfileUrl that uses the direct Python approach
ExtractSteamProfileUrl() {
    LogMessage("Extracting and processing Steam profile URL directly in Python...")
    
    ; Run the consolidated URL extraction and processing function that directly uses SteamProfileManager
    ; without the steam_bridge.py intermediary
    urlResult := RunPythonDetector("extract_and_process_url")
    LogMessage("Direct Python URL extraction and processing result: " urlResult)
    
    ; Parse the OCR output to get the URL and processing status
    steamProfileUrl := ""
    processingSuccess := false
    apiSubmissionSuccess := false
    savedToFallback := false
    
    ; Parse the URL first
    if InStr(urlResult, "URL_EXTRACTION_RESULT=1") {
        ; Try to extract the URL from the output
        if RegExMatch(urlResult, "URL=([^\r\n]+)", &match) {
            steamProfileUrl := Trim(match[1])
            LogMessage("Successfully extracted Steam profile URL: " steamProfileUrl)
        }
    } else {
        ; Extract error message if available
        errorMsg := "Unknown error"
        if RegExMatch(urlResult, "URL_EXTRACTION_ERROR=([^\r\n]+)", &match)
            errorMsg := Trim(match[1])
        LogMessage("Failed to extract URL: " errorMsg)
    }
    
    ; Parse the processing results
    if InStr(urlResult, "URL_PROCESSING_RESULT=1") {
        processingSuccess := true
        LogMessage("URL processing was successful")
        
        ; Check for API submission success
        if InStr(urlResult, "API_SUBMISSION=SUCCESS") {
            apiSubmissionSuccess := true
            LogMessage("Successfully submitted to API endpoint")
        } 
        
        ; Check if saved to fallback file
        if InStr(urlResult, "SAVED_TO_FALLBACK=1") {
            savedToFallback := true
            LogMessage("URL was saved to fallback file for later processing")
        }
    } else if InStr(urlResult, "URL_PROCESSING_RESULT=0") {
        ; Extract processing error if available
        processingError := "Unknown processing error"
        if RegExMatch(urlResult, "URL_PROCESSING_ERROR=([^\r\n]+)", &match)
            processingError := Trim(match[1])
        LogMessage("URL processing failed: " processingError)
    }
    
    ; Close the tab and overlay
    tabCloseSuccess := CloseTabAndOverlay(urlResult)
    
    ; Log the complete result for debugging
    LogMessage("URL extraction complete - URL: " steamProfileUrl)
    LogMessage("Processing success: " processingSuccess)
    LogMessage("API submission: " (apiSubmissionSuccess ? "Successful" : "Failed"))
    LogMessage("Saved to fallback: " (savedToFallback ? "Yes" : "No"))
    LogMessage("Tab close success: " tabCloseSuccess)
    
    return steamProfileUrl
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

; Enhanced ProcessPlayersGridMethod with dual-button detection approach and retry logic
ProcessPlayersGridMethod() {
    LogMessage("Processing players using grid method with improved profile popup detection...")
    
    ; Default constants for grid scanning
    defaultStartX := 720       ; X coordinate to start scanning
    defaultStartY := 326       ; Default Y coordinate to start scanning (fallback)
    endY := 836                ; Y coordinate to stop scanning (safety limit)
    
    ; Counter for profiles found
    profilesFound := 0
    
    ; Counter for consecutive failures
    consecutiveFailures := 0
    
    ; Flag to track if we have a next position from icon detection
    haveNextIconPosition := false
    nextClickX := 0
    nextClickY := 0
    
    ; Simply press Escape to view the scoreboard
    LogMessage("Opening scoreboard with Escape key...")
    Send "{Escape}"
    Sleep 1000
    
    ; Take a screenshot for attention icon detection
    LogMessage("Searching for attention icons...")
    CaptureScreenshot()
    ; Sleep 800
    
    ; Search in the right side area for attention icons
    firstIconResult := RunPythonDetector("find_first_attention_icon 1358 290 38 450")
    LogMessage("First icon search result: " firstIconResult)
    
    ; Check if an icon was found and get its coordinates
    if InStr(firstIconResult, "ATTENTION_ICON_FOUND=1") {
        if RegExMatch(firstIconResult, "PLAYER_CLICK_COORDS=(\d+),(\d+)", &coordMatch) {
            startX := Integer(coordMatch[1])
            startY := Integer(coordMatch[2])
            LogMessage("Found first attention icon! Starting at: X=" startX ", Y=" startY)
        } else {
            ; Fall back to defaults if coordinates couldn't be parsed
            startX := defaultStartX
            startY := defaultStartY
            LogMessage("Attention icon found but couldn't parse coordinates. Using defaults: X=" startX ", Y=" startY)
        }
    } else {
        LogMessage("No attention icons found in scoreboard. This might be an empty match or scoreboard not showing.")
        LogMessage("Disconnecting from match since no players to analyze...")
        DisconnectFromMatch()
        return false
    }
    
    ; Iterate through the player grid using initial position
    currentX := startX
    currentY := startY
    
    while (currentY <= endY) {  ; Keep the safety limit to prevent infinite loops
        LogMessage("Checking player at coordinates: " currentX "," currentY)
        
        ; Click at the current position
        Click currentX, currentY
        Sleep 900  ; Wait for any profile window to appear
        
        ; Take a screenshot to check if profile details loaded
        CaptureScreenshot()
        ; Sleep 800  ; Wait for screenshot to be saved
        
        ; Perform profile analysis (includes dual-button detection, sympathies, medals, and next attention icon check)
        LogMessage("Performing profile analysis with dual-button detection...")
        analysisResult := RunPythonDetector("analyze_profile " currentX " " currentY)
        LogMessage("Profile analysis result: " analysisResult)
        
        ; Parse the initial analysis results
        profile_popup_detected := InStr(analysisResult, "PROFILE_POPUP_DETECTED=1")
        profile_button_found := InStr(analysisResult, "PROFILE_BUTTON_FOUND=1")
        message_button_found := InStr(analysisResult, "MESSAGE_BUTTON_FOUND=1")
        three_plus_medals_found := InStr(analysisResult, "THREE_PLUS_MEDALS_FOUND=1")
        five_year_medal_found := InStr(analysisResult, "FIVE_YEAR_MEDAL_FOUND=1")
        unwanted_medals_found := InStr(analysisResult, "UNWANTED_MEDALS_FOUND=1")
        more_medals_available := InStr(analysisResult, "CLICK_TO_SEE_MORE_MEDALS=1")
        too_many_sympathies := InStr(analysisResult, "TOO_MANY_SYMPATHIES=1")
        
        ; Check for next attention icon coordinates
        haveNextIconPosition := InStr(analysisResult, "NEXT_ATTENTION_ICON_FOUND=1")
        if (haveNextIconPosition) {
            if RegExMatch(analysisResult, "NEXT_CLICK_COORDS=(\d+),(\d+)", &nextCoordMatch) {
                nextClickX := Integer(nextCoordMatch[1])
                nextClickY := Integer(nextCoordMatch[2])
                LogMessage("Found next player position at: " nextClickX "," nextClickY " (from attention icon)")
            } else {
                haveNextIconPosition := false
            }
        }
        
        ; Check if profile popup was properly detected (both buttons found)
        if (!profile_popup_detected) {
            ; Log detailed information about which button was missing
            buttonStatus := "Neither button found"
            if (profile_button_found && !message_button_found)
                buttonStatus := "Profile button found, message button missing"
            else if (!profile_button_found && message_button_found)
                buttonStatus := "Message button found, profile button missing"
            else if (profile_button_found && message_button_found)
                buttonStatus := "Both buttons found but spatial relationship invalid"
                
            LogMessage("Profile popup not detected: " buttonStatus)
            
            ; New retry logic: Try clicking again at the same position
            LogMessage("Attempting retry click at the same position: " currentX "," currentY)
            Click currentX, currentY
            Sleep 900  ; Wait for profile window to appear after second click
            
            ; Take another screenshot
            CaptureScreenshot()
            ; Sleep 800
            
            ; Perform profile analysis again
            LogMessage("Performing profile analysis after retry click...")
            retryAnalysisResult := RunPythonDetector("analyze_profile " currentX " " currentY)
            LogMessage("Retry analysis result: " retryAnalysisResult)
            
            ; Check if profile popup is detected after retry
            profile_popup_detected := InStr(retryAnalysisResult, "PROFILE_POPUP_DETECTED=1")
            
            if (profile_popup_detected) {
                LogMessage("Profile popup detected after retry click! Continuing with analysis.")
                
                ; Update all flags from retry analysis
                profile_button_found := InStr(retryAnalysisResult, "PROFILE_BUTTON_FOUND=1")
                message_button_found := InStr(retryAnalysisResult, "MESSAGE_BUTTON_FOUND=1")
                three_plus_medals_found := InStr(retryAnalysisResult, "THREE_PLUS_MEDALS_FOUND=1")
                five_year_medal_found := InStr(retryAnalysisResult, "FIVE_YEAR_MEDAL_FOUND=1")
                unwanted_medals_found := InStr(retryAnalysisResult, "UNWANTED_MEDALS_FOUND=1")
                more_medals_available := InStr(retryAnalysisResult, "CLICK_TO_SEE_MORE_MEDALS=1")
                too_many_sympathies := InStr(retryAnalysisResult, "TOO_MANY_SYMPATHIES=1")
                
                ; Update any next attention icon information
                haveNextIconPosition := InStr(retryAnalysisResult, "NEXT_ATTENTION_ICON_FOUND=1")
                if (haveNextIconPosition) {
                    if RegExMatch(retryAnalysisResult, "NEXT_CLICK_COORDS=(\d+),(\d+)", &nextCoordMatch) {
                        nextClickX := Integer(nextCoordMatch[1])
                        nextClickY := Integer(nextCoordMatch[2])
                        LogMessage("Found next player position at: " nextClickX "," nextClickY " (from attention icon in retry)")
                    } else {
                        haveNextIconPosition := false
                    }
                }
                
                ; Use the retry analysis result for further processing
                analysisResult := retryAnalysisResult
            } else {
                ; Increment consecutive failures counter since retry also failed
                consecutiveFailures++
                LogMessage("Profile popup still not detected after retry. Consecutive failures: " consecutiveFailures)
                
                ; After 3 consecutive failures, check if we should exit
                if (consecutiveFailures >= 3) {
                    LogMessage("Three consecutive failures reached. Verifying options...")
                    
                    ; If we have a next position from icon detection, try that before giving up
                    if (haveNextIconPosition) {
                        LogMessage("Found next attention icon despite failures. Will try that position.")
                        consecutiveFailures := 1  ; Reset but not to zero to keep some caution
                    } else {
                        LogMessage("No next attention icon found after 3 failures. Exiting to lobby...")
                        
                        ; Use console to disconnect from match
                        DisconnectFromMatch()
                        
                        ; Return true to indicate we've finished with this map
                        return true
                    }
                }
            }
        } else {
            ; Reset consecutive failures counter since we found a profile popup
            consecutiveFailures := 0
        }
        
        ; Extract sympathies sum for logging
        sympathies_sum := 0
        if RegExMatch(analysisResult, "SYMPATHIES_SUM=(\d+)", &sumMatch)
            sympathies_sum := Integer(sumMatch[1])
        
        ; Extract medal count for logging
        medalCount := 0
        if RegExMatch(analysisResult, "MEDAL_COUNT=(\d+)", &countMatch)
            medalCount := Integer(countMatch[1])
        
        ; Extract profile button coordinates if popup detected
        profileButtonX := 0
        profileButtonY := 0
        if (profile_popup_detected && RegExMatch(analysisResult, "PROFILE_BUTTON_COORDS=(\d+),(\d+)", &coordMatch)) {
            profileButtonX := Integer(coordMatch[1])
            profileButtonY := Integer(coordMatch[2])
            LogMessage("Profile button found at coordinates: " profileButtonX "," profileButtonY)
        }
        
        ; Log comprehensive analysis results
        LogMessage("Analysis summary:")
        LogMessage("- Profile popup detected: " (profile_popup_detected ? "Yes" : "No"))
        if (profile_popup_detected) {
            LogMessage("- Sympathies sum: " sympathies_sum)
            LogMessage("- Too many sympathies: " (too_many_sympathies ? "Yes" : "No"))
            LogMessage("- Three+ medals found: " (three_plus_medals_found ? "Yes" : "No"))
            LogMessage("- 5-year veteran coin found: " (five_year_medal_found ? "Yes" : "No"))
            LogMessage("- Unwanted medals found: " (unwanted_medals_found ? "Yes" : "No"))
            LogMessage("- More medals available: " (more_medals_available ? "Yes" : "No"))
            LogMessage("- Medal count: " medalCount)
        }
        LogMessage("- Next player position from icon: " (haveNextIconPosition ? "Yes" : "No"))
        
        ; Make initial decision
        shouldContinue := true
        
        ; Early skip conditions (in optimized order)
        if (!profile_popup_detected) {
            LogMessage("No profile popup detected, skipping player")
            shouldContinue := false
        } else if (too_many_sympathies) {
            LogMessage("Player has too many sympathies (" sympathies_sum " > 100), skipping player")
            shouldContinue := false
        } else if (unwanted_medals_found) {
            LogMessage("Unwanted medals found, skipping player")
            shouldContinue := false
        } else if (!three_plus_medals_found) {
            LogMessage("Less than 3 medals found, skipping player")
            shouldContinue := false
        }
        
        ; If we should continue and more medals are available, click to see more medals
        maxArrowClicks := 3  ; Maximum number of times to click the arrow to prevent infinite loops
        arrowClickCount := 0
        
        ; If we need to continue and more medals are available, click on the arrow
        while (shouldContinue && more_medals_available && arrowClickCount < maxArrowClicks) {
            ; Default arrow coordinates (fallback if detection fails)
            arrowX := currentX + 394
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
            Sleep 700  ; Wait for UI to update
            
            ; Take a new screenshot after clicking the arrow
            CaptureScreenshot()
            ; Sleep 800  ; Wait for screenshot to be saved
            
            ; Analyze again with the new screenshot
            LogMessage("Performing follow-up profile analysis after arrow click...")
            followUpResult := RunPythonDetector("analyze_profile " currentX " " currentY)
            
            ; Update the state variables that might change
            profile_popup_detected := InStr(followUpResult, "PROFILE_POPUP_DETECTED=1")
            if (!profile_popup_detected) {
                LogMessage("Profile popup no longer detected after arrow click!")
                shouldContinue := false
                break
            }
            
            five_year_medal_found := five_year_medal_found || InStr(followUpResult, "FIVE_YEAR_MEDAL_FOUND=1")
                
            if (!unwanted_medals_found)
                unwanted_medals_found := InStr(followUpResult, "UNWANTED_MEDALS_FOUND=1")
                
            more_medals_available := InStr(followUpResult, "CLICK_TO_SEE_MORE_MEDALS=1")
            
            ; Update medal count for logging
            if RegExMatch(followUpResult, "MEDAL_COUNT=(\d+)", &countMatch)
                medalCount := Integer(countMatch[1])
                
            ; Check for updated next attention icon position
            if InStr(followUpResult, "NEXT_ATTENTION_ICON_FOUND=1") {
                haveNextIconPosition := true
                if RegExMatch(followUpResult, "NEXT_CLICK_COORDS=(\d+),(\d+)", &nextCoordMatch) {
                    nextClickX := Integer(nextCoordMatch[1])
                    nextClickY := Integer(nextCoordMatch[2])
                    LogMessage("Updated next player position: " nextClickX "," nextClickY)
                } else {
                    haveNextIconPosition := false
                }
            }
                
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
                Sleep 2000  ; Give Steam browser time to open
                
                ; Take screenshot for URL OCR
                CaptureScreenshot()
                ; Sleep 800  ; Give enough time for screenshot to be saved
                
                ; Extract Steam profile URL
                steamProfileUrl := ExtractSteamProfileUrl()
                
                ; Increment profiles found counter if URL was extracted
                if (steamProfileUrl) {
                    profilesFound++
                    LogMessage("Profile #" profilesFound " processed successfully with URL: " steamProfileUrl)
                }
            } else {
                LogMessage("Player has 3+ medals but no 5-year coin, skipping profile")
                
                ; Need to close profile details in this case
                LogMessage("Clicking again to close profile details")
                Click currentX, currentY
                Sleep 300
            }
        } else {
            ; Only click to close profile details if we didn't open Steam profile
            LogMessage("Clicking again to close profile details")
            Click currentX, currentY
            Sleep 300
        }
        
        ; Move to the next row using either icon-based position or default offset
        if (haveNextIconPosition) {
            ; Use the position from attention icon detection
            currentX := nextClickX
            currentY := nextClickY
            LogMessage("Moving to next player using attention icon coordinates: " currentX "," currentY)
        } else {
            ; No more attention icons found - we've reached the end of human players
            LogMessage("No more attention icons found - we've reached the end of human players in this match")
            LogMessage("Disconnecting from match to save time...")
            DisconnectFromMatch()
            return profilesFound > 0
        }
    }
    
    ; This should rarely be reached since we now exit when no more attention icons are found
    LogMessage("Grid scanning completed. Found " profilesFound " qualified player profiles.")
    return profilesFound > 0
}

; Function to ensure the scoreboard is visible
EnsureScoreboardVisible(&iconStartY := 0) {
    LogMessage("Ensuring scoreboard is visible...")
    
    ; Make sure CS2 is the active window
    activateResult := ActivateCS2Window()
    if (activateResult = 0) {
        LogMessage("Failed to activate CS2 window in EnsureScoreboardVisible - cannot continue")
        return false
    } else if (activateResult = 3) {
        LogMessage("CS2 was relaunched during scoreboard check - aborting current operation")
        return false
    }
    
    ; Define ROI for scoreboard icon
    iconRoiX := 500
    iconRoiY := 225
    iconRoiWidth := 25
    iconRoiHeight := 165
    
    ; Try to show scoreboard up to 3 times
    Loop 3 {
        ; Press Escape to open the pause menu/scoreboard
        LogMessage("Pressing Escape to view scoreboard (attempt " A_Index "/3)...")
        Send "{Escape}"
        Sleep 500  ; Wait 2 seconds for scoreboard to appear
        
        ; Take a screenshot
        CaptureScreenshot()
        ; Sleep 800  ; Wait for screenshot to be saved
        
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
    ; MsgBox("Failed to detect CS2 scoreboard after 3 attempts.`n`nPlease check if the game is running correctly.", "Scoreboard Detection Error", "OK Icon!")
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

    ; Set up timeout for match processing - 5 minutes (300,000 ms)
    startTime := A_TickCount
    timeout := 300000  ; 5 minutes in milliseconds

    ; Wait a few seconds for the match to fully load
    Sleep 500

    ; Store the global timeout start time for access in other functions
    Global MATCH_PROCESS_START_TIME := startTime
    Global MATCH_PROCESS_TIMEOUT := timeout

    ; Create a timer that will check for timeout regularly
    SetTimer CheckMatchTimeout, 10000  ; Check every 10 seconds

    ; Track if processing is successful
    success := false

    try {

        ; LogMessage("Calling Node.js to collect player data...")

        ; exitCode := RunWait("python ..\python_services\bridge_script.py")
        
        ; if (exitCode != 0) {
        ;    LogMessage("Node.js player data collection failed")
        ;} else {
        ;    LogMessage("Node.js player data collection successful")
        ;}

        ; Process players using the simplified grid method
        success := ProcessPlayersGridMethod()

    } catch Error as e {
        LogMessage("Error in match processing: " e.Message)
    } finally {
        ; Stop the timeout timer
        SetTimer CheckMatchTimeout, 0

        ; Return to main menu using ESC regardless of outcome
        ReturnToMainMenu()
        ; Clean up screenshots that are no longer needed
        CleanupScreenshots()
    }

    if (success) {
        LogMessage("Match processing completed successfully")
        return true
    } else {
        LogMessage("Match processing completed but no profiles were found")
        return false
    }
}

; Separate function to check for timeout, runs on timer
CheckMatchTimeout() {
    currentTime := A_TickCount
    elapsedTime := currentTime - MATCH_PROCESS_START_TIME
    
    if (elapsedTime > MATCH_PROCESS_TIMEOUT) {
        ; Log the timeout
        LogMessage("TIMEOUT: Match processing exceeded " MATCH_PROCESS_TIMEOUT/1000 " seconds limit")
        
        ; Kill the timer to prevent duplicate calls
        SetTimer CheckMatchTimeout, 0
        
        ; Kill CS2 and exit
        LogMessage("Processing timeout detected - killing CS2 and exiting script")
        KillCS2Process()
        ExitApp
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
    Sleep 500
    
    return true
}

