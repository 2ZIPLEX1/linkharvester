; CS2 Automation Script for AutoHotkey v2
; Main script file - handles game startup and map selection
#Requires AutoHotkey v2.0

; Include helper and module files
#Include "CS2_Helpers.ahk"
#Include "CS2_Matchmaking.ahk"
#Include "CS2_InGame.ahk"
#Include "CS2_Hotkeys.ahk"

; Initialize globals and setup
Global CS2_CONFIG := LoadConfiguration()
Global LOG_FILE := A_MyDocuments "\AutoHotkey\cs2_automation.log"

; Make sure log directory exists
If !DirExist(A_MyDocuments "\AutoHotkey")
    DirCreate A_MyDocuments "\AutoHotkey"

LogMessage("=== CS2 Automation Script Started ===")
LogMessage("AHK Version: " A_AhkVersion)
LogMessage("Script Path: " A_ScriptFullPath)
LogMessage("Log File: " LOG_FILE)

; Map selection coordinates
; These are the center points of each map card in the selection screen
Global MAP_COORDINATES := Map(
    "Sigma", {x: 380, y: 430},
    "Delta", {x: 650, y: 430},
    "Dust2", {x: 920, y: 430},
    "Hostage", {x: 1200, y: 430}
)

; Maps to cycle through
Global MAP_CYCLE := ["Sigma", "Delta", "Dust2", "Hostage"]
Global CURRENT_MAP_INDEX := 1

; Main function
Main()

; Main function
Main() {
    Global CS2_CONFIG
    
    ; Display important settings
    LogMessage("CS2 Path: " CS2_CONFIG["cs2_executable"])
    LogMessage("Steam Path: " CS2_CONFIG["steam_executable"])
    
    ; Display minimal startup message
    MsgBox("CS2 Automation Starting`n`nHotkeys: Ctrl+Alt+X = Emergency Exit, Ctrl+Alt+P = Pause/Resume`n`nClick OK to begin.", "CS2 Automation", "OK")
    
    ; Check if CS2 is running
    if (!EnsureCS2Running()) {
        LogMessage("Failed to ensure CS2 is running. Exiting script.")
        return
    }
    
    ; Begin map cycle
    RunMapCycle()
}

; Update the RunMapCycle function in cs2_automation.ahk

RunMapCycle() {
    Global CURRENT_MAP_INDEX, MAP_CYCLE, CS2_CONFIG
    
    ; For the initial testing, just use the first map (Sigma)
    currentMap := MAP_CYCLE[CURRENT_MAP_INDEX]
    LogMessage("Processing map: " currentMap)
    
    ; Navigate to matchmaking and select the current map
    if (!SelectMap(currentMap)) {
        LogMessage("Failed to select map: " currentMap)
        return
    }
    
    ; Log that we're waiting for match
    LogMessage("Map selected, now waiting for match to be found and joined...")
    
    ; Increase timeout for waiting - use a much longer timeout
    ; This needs to be very long since we need to wait through:
    ; 1. Initial matchmaking search
    ; 2. "YOUR MATCH IS READY!" screen display
    ; 3. Loading into server (can take quite a while)
    ; 4. Finally spectate button appears
    originalTimeout := CS2_CONFIG["max_wait_for_match"]
    CS2_CONFIG["max_wait_for_match"] := 600  ; 10 minutes
    
    ; Wait for match outcome
    matchOutcome := WaitForMatchOutcome()
    
    ; Reset timeout
    CS2_CONFIG["max_wait_for_match"] := originalTimeout
    
    LogMessage("Match outcome for " currentMap ": " matchOutcome)
    
    if (matchOutcome = "success") {
        ; Handle successful match
        LogMessage("Successfully joined " currentMap " match!")
        
        ; Process the match (view players, etc.)
        ProcessMatch()
        
        ; After match is done
        LogMessage("Finished with " currentMap " match")
    }
    else if (matchOutcome = "failure" || matchOutcome = "timeout") {
        LogMessage("Failed to join " currentMap " match: " matchOutcome)
        
        ; Take a final screenshot to help debug
        CaptureFullscreenScreenshot()
        
        ; Try to return to main menu to recover
        Send "{Escape}"
        Sleep 2000
        Send "{Escape}"
        Sleep 2000
    }
    
    LogMessage("Map cycle completed")
    MsgBox("CS2 Automation completed`n`nOutcome: " matchOutcome, "Done", "OK")
}

; Function to select a specific map
SelectMap(mapName) {
    Global CS2_CONFIG, MAP_COORDINATES
    
    LogMessage("Selecting map: " mapName)
    
    ; Make sure CS2 is the active window
    WinActivate "Counter-Strike"
    Sleep 2000
    
    ; 1. Press Play button
    LogMessage("Clicking Play button at coordinates: " CS2_CONFIG["play_button_x"] "," CS2_CONFIG["play_button_y"])
    Click CS2_CONFIG["play_button_x"], CS2_CONFIG["play_button_y"]
    Sleep CS2_CONFIG["wait_between_clicks"]
    
    ; 2. Select Matchmaking mode
    LogMessage("Selecting matchmaking mode at coordinates: " CS2_CONFIG["mode_selection_x"] "," CS2_CONFIG["mode_selection_y"])
    Click CS2_CONFIG["mode_selection_x"], CS2_CONFIG["mode_selection_y"]
    Sleep CS2_CONFIG["wait_between_clicks"]
    
    ; 3. Select League (Casual)
    LogMessage("Selecting casual league at coordinates: " CS2_CONFIG["league_selection_x"] "," CS2_CONFIG["league_selection_y"])
    Click CS2_CONFIG["league_selection_x"], CS2_CONFIG["league_selection_y"]
    Sleep CS2_CONFIG["wait_between_clicks"]
    
    ; 4. Select the specific map
    if (!MAP_COORDINATES.Has(mapName)) {
        LogMessage("Error: Unknown map name: " mapName)
        return false
    }
    
    mapCoordinates := MAP_COORDINATES[mapName]
    LogMessage("Selecting " mapName " map at coordinates: " mapCoordinates.x "," mapCoordinates.y)
    Click mapCoordinates.x, mapCoordinates.y
    Sleep CS2_CONFIG["wait_between_clicks"]
    
    ; 5. Accept/Start Match
    LogMessage("Clicking Accept Match at coordinates: " CS2_CONFIG["accept_match_x"] "," CS2_CONFIG["accept_match_y"])
    Click CS2_CONFIG["accept_match_x"], CS2_CONFIG["accept_match_y"]
    Sleep CS2_CONFIG["wait_between_clicks"]
    
    ; For debugging, take a screenshot of current state
    CaptureScreenshot()
    
    LogMessage("Map selection sequence completed for: " mapName)
    return true
}