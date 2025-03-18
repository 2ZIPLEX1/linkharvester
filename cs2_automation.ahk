; CS2 Automation Script for AutoHotkey v2
; This script launches CS2 if not running, joins a match, and views the player list

#Requires AutoHotkey v2.0

; Set up logging to OneDrive Documents folder
LogDir := A_MyDocuments "\AutoHotkey"
if !DirExist(LogDir)
    DirCreate LogDir
LOG_FILE := LogDir "\cs2_automation.log"

; Load configuration from simple text file instead of JSON
ConfigFile := LogDir "\data\config.txt"
Config := Map()

; Attempt to load configuration
if FileExist(ConfigFile) {
    try {
        FileContent := FileRead(ConfigFile)
        Loop Parse, FileContent, "`n", "`r"
        {
            if InStr(A_LoopField, "=") {
                parts := StrSplit(A_LoopField, "=", , 2)
                if parts.Length = 2
                    Config[Trim(parts[1])] := Trim(parts[2])
            }
        }
        LogMessage("Configuration loaded successfully")
    } catch Error as e {
        LogMessage("Error loading configuration: " e.Message)
    }
} else {
    LogMessage("Configuration file not found: " ConfigFile)
}

; Configuration - use values from config file or defaults
CS2_EXECUTABLE := Config.Has("cs2_executable") ? Config["cs2_executable"] : "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe"

; Check common Steam installation paths
if Config.Has("steam_executable")
    STEAM_EXECUTABLE := Config["steam_executable"]
else if FileExist("D:\SteamLibrary\Steam.exe")
    STEAM_EXECUTABLE := "D:\SteamLibrary\Steam.exe"
else if FileExist("C:\Program Files (x86)\Steam\steam.exe")
    STEAM_EXECUTABLE := "C:\Program Files (x86)\Steam\steam.exe"
else if FileExist("C:\Program Files\Steam\steam.exe")
    STEAM_EXECUTABLE := "C:\Program Files\Steam\steam.exe"
else
    STEAM_EXECUTABLE := "steam.exe"  ; Rely on PATH if we can't find it

; UI Coordinates - use values from config file or defaults
PlayButtonX := Config.Has("play_button_x") ? Config["play_button_x"] : 960
PlayButtonY := Config.Has("play_button_y") ? Config["play_button_y"] : 540
ModeSelectionX := Config.Has("mode_selection_x") ? Config["mode_selection_x"] : 960
ModeSelectionY := Config.Has("mode_selection_y") ? Config["mode_selection_y"] : 600
FindMatchX := Config.Has("find_match_x") ? Config["find_match_x"] : 960
FindMatchY := Config.Has("find_match_y") ? Config["find_match_y"] : 700
AcceptMatchX := Config.Has("accept_match_x") ? Config["accept_match_x"] : 960
AcceptMatchY := Config.Has("accept_match_y") ? Config["accept_match_y"] : 580

; Timing settings
MatchTimeout := Config.Has("match_timeout") ? Config["match_timeout"] : 180
MatchStartWait := Config.Has("match_start_wait") ? Config["match_start_wait"] : 30

; Log function
LogMessage(message) {
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    FileAppend timestamp " - " message "`n", LOG_FILE
}

; Check if a process is running
IsProcessRunning(processName) {
    return ProcessExist(processName)
}

; Launch CS2
LaunchCS2() {
    LogMessage("Attempting to launch CS2...")
    LogMessage("CS2 Executable: " CS2_EXECUTABLE)
    
    ; Check if CS2 executable exists
    if !FileExist(CS2_EXECUTABLE) {
        LogMessage("Error: CS2 executable not found at: " CS2_EXECUTABLE)
        MsgBox("CS2 executable not found at: " CS2_EXECUTABLE "`n`nPlease update the configuration file.", "Error", "Icon!")
        return false
    }
    
    ; Check if Steam is running
    If !IsProcessRunning("steam.exe") {
        LogMessage("Steam not running. Launching Steam...")
        LogMessage("Steam Executable: " STEAM_EXECUTABLE)
        Run STEAM_EXECUTABLE
        Sleep 10000  ; Wait for Steam to initialize
    }
    
    ; Launch CS2
    LogMessage("Launching CS2...")
    Run CS2_EXECUTABLE
    
    ; Wait for CS2 to launch
    try {
        WinWait "Counter-Strike", , 60
    } catch {
        LogMessage("Error: Timed out waiting for CS2 to launch")
        return false
    }
    
    ; Activate CS2 window
    WinActivate "Counter-Strike"
    LogMessage("CS2 launched and activated")
    Sleep 5000  ; Wait for the game to fully load
    return true
}

; Navigate to find a match
FindMatch() {
    LogMessage("Finding a match...")
    
    ; Make sure CS2 is the active window
    WinActivate "Counter-Strike"
    Sleep 2000
    
    ; Press Play button (assuming we're at the main menu)
    LogMessage("Pressing Play button at coordinates: " PlayButtonX "," PlayButtonY)
    Click PlayButtonX, PlayButtonY
    Sleep 2000
    
    ; Select Competitive mode
    LogMessage("Selecting game mode at coordinates: " ModeSelectionX "," ModeSelectionY)
    Click ModeSelectionX, ModeSelectionY
    Sleep 1000
    
    ; Click Find Match
    LogMessage("Clicking Find Match at coordinates: " FindMatchX "," FindMatchY)
    Click FindMatchX, FindMatchY
    Sleep 1000
    
    ; For debugging, take a screenshot of current state
    LogMessage("Taking screenshot of current state...")
    Send "{PrintScreen}"
    
    ; We'll use a simplified approach for demo purposes
    ; Instead of waiting for a specific color, wait briefly and simulate finding a match
    LogMessage("Waiting for match (simulated for demo)...")
    Sleep 5000  ; Wait for 5 seconds
    
    MsgBox("The script would normally wait for a match.`n`nFor demonstration, click OK to simulate finding a match.", "CS2 Automation", "OK")
    
    LogMessage("Match found (simulated). Moving to player list view...")
    return true
}

; View player list
ViewPlayerList() {
    LogMessage("Viewing player list...")
    
    ; Press Tab to view scoreboard (player list)
    LogMessage("Pressing Tab to view scoreboard...")
    Send "{Tab down}"
    Sleep 2000
    
    ; Take screenshot of player list
    LogMessage("Taking screenshot of player list...")
    Send "{PrintScreen}"
    LogMessage("Screenshot taken of player list")
    
    ; Release Tab
    Send "{Tab up}"
    Sleep 500
    
    return true
}

; Main function
Main() {
    LogMessage("=== Script Started ===")
    LogMessage("AHK Version: " A_AhkVersion)
    LogMessage("Script Path: " A_ScriptFullPath)
    LogMessage("Log File: " LOG_FILE)
    
    ; Display important settings
    LogMessage("CS2 Path: " CS2_EXECUTABLE)
    LogMessage("Steam Path: " STEAM_EXECUTABLE)
    
    MsgBox("CS2 Automation Script Starting`n`nCS2 Path: " CS2_EXECUTABLE "`nLog File: " LOG_FILE, "CS2 Automation", "OK")
    
    ; Check if CS2 is running
    LogMessage("Checking if CS2 is running...")
    try {
        if WinExist("Counter-Strike") {
            LogMessage("CS2 is already running. Window activated.")
            WinActivate "Counter-Strike"
            Sleep 2000
        } else {
            LogMessage("CS2 is not running, launching it...")
            if (!LaunchCS2()) {
                LogMessage("Failed to launch CS2. Exiting script.")
                return
            }
        }
    } catch Error as e {
        LogMessage("Error checking CS2 status: " e.Message)
        ; CS2 is not running, launch it
        if (!LaunchCS2()) {
            LogMessage("Failed to launch CS2. Exiting script.")
            return
        }
    }
    
    ; Try to find a match
    if (!FindMatch()) {
        LogMessage("Failed to find a match. Exiting script.")
        return
    }
    
    ; View player list
    ViewPlayerList()
    
    LogMessage("Script completed successfully")
    MsgBox("CS2 Automation completed successfully", "Done", "OK")
}

; Run the main function
Main()