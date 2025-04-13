; CS2 Automation Script for AutoHotkey v2
; Main script file - handles game startup and map selection
#Requires AutoHotkey v2.0

; Include helper and module files
#Include "Helpers.ahk"
#Include "Matchmaking.ahk"
#Include "InGame.ahk"
#Include "Hotkeys.ahk"
#Include "API_Integration.ahk"

; Initialize globals and setup
Global LOG_FILE := "C:\LinkHarvesterScript\logs\automation.log"

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

; Map coordinates in a Map object for easy reference
Global MAP_COORDINATES := Map(
    "Sigma", {x: 502, y: 570, name: "Sigma"},
    "Delta", {x: 868, y: 570, name: "Delta"},
    "DustII", {x: 1230, y: 570, name: "Dust II"},
    "Hostage", {x: 1596, y: 570, name: "Hostage Group"}
)

; Main function
Main()

; Main function
Main() {
    ; Display minimal startup message
    ; MsgBox("CS2 Automation Starting`n`nHotkeys: Ctrl+Alt+X = Emergency Exit, Ctrl+Alt+P = Pause/Resume`n`nClick OK to begin.", "CS2 Automation", "OK")
    
    ; Clear the URL cache at the beginning of each server round
    ClearUrlCache()

    ; Process any previously saved IDs on startup
    ProcessSavedIDs()
    
    ; Check if CS2 is running
    if (!EnsureCS2Running()) {
        LogMessage("Failed to ensure CS2 is running. Exiting script.")
        return
    }
    
    ; Run three complete rounds
    Loop 1 {
        roundNumber := A_Index
        LogMessage("Starting round " roundNumber " of 3")
        
        ; Run all four maps in this round
        RunAllMaps(roundNumber)
        
        LogMessage("Completed round " roundNumber " of 3")
    }
    
    LogMessage("All rounds completed!")
    ; MsgBox("CS2 Automation completed`n`nAll 3 rounds with 4 maps each have been processed.", "Done", "OK")

    ; Exit the script
    LogMessage("All tasks completed. Exiting AHK...")
    ExitApp
}

RunAllMaps(roundNumber) {
    ; Get all map keys in the desired order
    ; mapKeys := ["Sigma", "Delta", "DustII", "Hostage"]
    mapKeys := ["Sigma"]
    
    ; Process each map in order
    for mapKey in mapKeys {
        ; Ensure we're at the main menu first
        if (!EnsureAtMainMenu()) {
            LogMessage("Failed to return to main menu before starting " mapKey)
            continue  ; Skip this map if we can't get to main menu
        }
        
        ; Get map info
        mapInfo := MAP_COORDINATES[mapKey]
        
        LogMessage("Round " roundNumber ": Starting map " mapInfo.name)
        
        ; Run this map
        mapResult := RunMap(mapKey)
        
        ; Check for fatal error
        if (mapResult = "fatal_error") {
            LogMessage("Fatal error detected. Exiting script...")
            ; MsgBox("A fatal server connection error was detected.`n`nThe script will now exit.", "Fatal Error", 48)
            ExitApp  ; Exit the entire script
        }
        
        if (mapResult = true) {
            LogMessage("Round " roundNumber ": Successfully completed map " mapInfo.name)
        } else {
            LogMessage("Round " roundNumber ": Failed or skipped map " mapInfo.name)
        }
    }
}

RunMap(mapKey) {
    ; Get map info
    mapInfo := MAP_COORDINATES[mapKey]
    if (!mapInfo) {
        LogMessage("Unknown map key: " mapKey)
        return false
    }
    
    LogMessage("Starting " mapInfo.name " match automation")
    
    ; Navigate to matchmaking and select the map
    if (!SelectMap(mapKey)) {
        LogMessage("Failed to select " mapInfo.name " map")
        return false
    }
    
    ; Log that we're waiting for match
    LogMessage("Map " mapInfo.name " selected, now waiting for match to be found and joined...")
    
    ; Wait for match outcome
    matchOutcome := WaitForMatchOutcome()
    LogMessage("Match outcome for " mapInfo.name ": " matchOutcome)
    
    if (matchOutcome = "success") {
        ; Handle successful match
        LogMessage("Successfully joined " mapInfo.name " match!")
        
        ; Process the match (view players, etc.)
        ProcessMatch()
        
        ; After match is done
        LogMessage("Finished with " mapInfo.name " match")
        return true
    }
    else if (matchOutcome = "failure" || matchOutcome = "timeout") {
        LogMessage("Failed to join " mapInfo.name " match: " matchOutcome)
        
        ; Add CS2 termination for timeout scenario
        if (matchOutcome = "timeout") {
            LogMessage("Match timeout detected - killing CS2 process and exiting script...")
            KillCS2Process()
            ExitApp  ; Exit script immediately after killing the process
        } else {
            ; Try to return to main menu to recover for non-timeout failures
            Send "{Escape}"
            Sleep 1000
        }
        return false
    }
    
    return false
}

; Function to select a map
SelectMap(mapKey) {
    ; Get map info
    mapInfo := MAP_COORDINATES[mapKey]
    if (!mapInfo) {
        LogMessage("Unknown map key: " mapKey)
        return false
    }
    
    LogMessage("Selecting map: " mapInfo.name)
    
    ; Make sure CS2 is the active window
    WinActivate "Counter-Strike"
    Sleep 1000
    
    ; 1. Press Play button
    LogMessage("Clicking Play button at coordinates: " CONFIG.play_button_x "," CONFIG.play_button_y)
    Click CONFIG.play_button_x, CONFIG.play_button_y
    Sleep 1000
    
    ; 2. Select Matchmaking mode
    LogMessage("Selecting matchmaking mode at coordinates: " CONFIG.mode_selection_x "," CONFIG.mode_selection_y)
    Click CONFIG.mode_selection_x, CONFIG.mode_selection_y
    Sleep 500
    
    ; 3. Select League (Casual)
    LogMessage("Selecting casual league at coordinates: " CONFIG.league_selection_x "," CONFIG.league_selection_y)
    Click CONFIG.league_selection_x, CONFIG.league_selection_y
    Sleep 300
    
    ; 4. Select the specific map
    LogMessage("Selecting " mapInfo.name " map at coordinates: " mapInfo.x "," mapInfo.y)
    Click mapInfo.x, mapInfo.y
    Sleep 100
    
    ; 5. Accept/Start Match
    LogMessage("Clicking Accept Match at coordinates: " CONFIG.accept_match_x "," CONFIG.accept_match_y)
    Click 1550, 1030
    ; Sleep 500
    
    LogMessage("Map selection sequence completed for: " mapInfo.name)
    return true
}