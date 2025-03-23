; CS2 Automation Script for AutoHotkey v2
; Main script file - handles game startup and map selection
#Requires AutoHotkey v2.0

; Include helper and module files
#Include "CS2_Helpers.ahk"
#Include "CS2_Matchmaking.ahk"
#Include "CS2_InGame.ahk"
#Include "CS2_Hotkeys.ahk"

; Initialize globals and setup
Global LOG_FILE := "C:\LinkHarvesterScript\cs2_automation.log"

; Make sure log directory exists
If !DirExist(A_MyDocuments "\AutoHotkey")
    DirCreate A_MyDocuments "\AutoHotkey"

LogMessage("=== CS2 Automation Script Started ===")
LogMessage("AHK Version: " A_AhkVersion)
LogMessage("Script Path: " A_ScriptFullPath)
LogMessage("Log File: " LOG_FILE)

; Configuration
Global CONFIG := {
    wait_between_clicks: 1500,
    play_button_x: 985,
    play_button_y: 30,
    mode_selection_x: 813,
    mode_selection_y: 85,
    league_selection_x: 906,
    league_selection_y: 130,
    accept_match_x: 1695,
    accept_match_y: 1030
}

; Map coordinates
Global MAP_COORDINATES := Map(
    "Sigma", {x: 380, y: 430}
)

; Main function
Main()

; Main function
Main() {
    ; Display minimal startup message
    MsgBox("CS2 Automation Starting`n`nHotkeys: Ctrl+Alt+X = Emergency Exit, Ctrl+Alt+P = Pause/Resume`n`nClick OK to begin.", "CS2 Automation", "OK")
    
    ; Check if CS2 is running
    if (!EnsureCS2Running()) {
        LogMessage("Failed to ensure CS2 is running. Exiting script.")
        return
    }
    
    ; Run automation
    RunSigmaMatch()
}

RunSigmaMatch() {
    LogMessage("Starting Sigma match automation")
    
    ; Navigate to matchmaking and select Sigma map
    if (!SelectMap("Sigma")) {
        LogMessage("Failed to select Sigma map")
        return
    }
    
    ; Log that we're waiting for match
    LogMessage("Map selected, now waiting for match to be found and joined...")
    
    ; Wait for match outcome
    matchOutcome := WaitForMatchOutcome()
    
    LogMessage("Match outcome: " matchOutcome)
    
    if (matchOutcome = "success") {
        ; Handle successful match
        LogMessage("Successfully joined match!")
        
        ; Process the match (view players, etc.)
        ProcessMatch()
        
        ; After match is done
        LogMessage("Finished with match")
    }
    else if (matchOutcome = "failure" || matchOutcome = "timeout") {
        LogMessage("Failed to join match: " matchOutcome)
        
        ; Take a final screenshot to help debug
        CaptureScreenshot()
        
        ; Try to return to main menu to recover
        Send "{Escape}"
        Sleep 2000
        Send "{Escape}"
        Sleep 2000
    }
    
    LogMessage("Automation completed")
    MsgBox("CS2 Automation completed`n`nOutcome: " matchOutcome, "Done", "OK")
}

; Function to select the Sigma map
SelectMap(mapName) {
    LogMessage("Selecting map: " mapName)
    
    ; Make sure CS2 is the active window
    WinActivate "Counter-Strike"
    Sleep 2000
    
    ; 1. Press Play button
    LogMessage("Clicking Play button at coordinates: " CONFIG.play_button_x "," CONFIG.play_button_y)
    Click CONFIG.play_button_x, CONFIG.play_button_y
    Sleep CONFIG.wait_between_clicks
    
    ; 2. Select Matchmaking mode
    LogMessage("Selecting matchmaking mode at coordinates: " CONFIG.mode_selection_x "," CONFIG.mode_selection_y)
    Click CONFIG.mode_selection_x, CONFIG.mode_selection_y
    Sleep CONFIG.wait_between_clicks
    
    ; 3. Select League (Casual)
    LogMessage("Selecting casual league at coordinates: " CONFIG.league_selection_x "," CONFIG.league_selection_y)
    Click CONFIG.league_selection_x, CONFIG.league_selection_y
    Sleep CONFIG.wait_between_clicks
    
    ; 4. Select the specific map
    if (!MAP_COORDINATES.Has(mapName)) {
        LogMessage("Error: Unknown map name: " mapName)
        return false
    }
    
    mapCoordinates := MAP_COORDINATES[mapName]
    LogMessage("Selecting " mapName " map at coordinates: " mapCoordinates.x "," mapCoordinates.y)
    Click mapCoordinates.x, mapCoordinates.y
    Sleep CONFIG.wait_between_clicks
    
    ; 5. Accept/Start Match
    LogMessage("Clicking Accept Match at coordinates: " CONFIG.accept_match_x "," CONFIG.accept_match_y)
    Click CONFIG.accept_match_x, CONFIG.accept_match_y
    Sleep CONFIG.wait_between_clicks
    
    ; For debugging, take a screenshot of current state
    CaptureScreenshot()
    
    LogMessage("Map selection sequence completed for: " mapName)
    return true
}