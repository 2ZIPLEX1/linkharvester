; CS2 Automation Script for AutoHotkey v2
; This script navigates through the CS2 UI to join a match and handles success/failure scenarios

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

; UI Coordinates - Using updated coordinates
PlayButtonX := Config.Has("play_button_x") ? Config["play_button_x"] : 985
PlayButtonY := Config.Has("play_button_y") ? Config["play_button_y"] : 30
ModeSelectionX := Config.Has("mode_selection_x") ? Config["mode_selection_x"] : 813
ModeSelectionY := Config.Has("mode_selection_y") ? Config["mode_selection_y"] : 85
LeagueSelectionX := Config.Has("league_selection_x") ? Config["league_selection_x"] : 906
LeagueSelectionY := Config.Has("league_selection_y") ? Config["league_selection_y"] : 130
SelectSigmaX := Config.Has("select_sigma_x") ? Config["select_sigma_x"] : 504
SelectSigmaY := Config.Has("select_sigma_y") ? Config["select_sigma_y"] : 578
AcceptMatchX := Config.Has("accept_match_x") ? Config["accept_match_x"] : 1690
AcceptMatchY := Config.Has("accept_match_y") ? Config["accept_match_y"] : 1030

; Spectator button coordinates and color
SpectatorButtonX := Config.Has("spectator_button_x") ? Config["spectator_button_x"] : 1592
SpectatorButtonY := Config.Has("spectator_button_y") ? Config["spectator_button_y"] : 1031
SpectatorButtonColor := Config.Has("spectator_button_color") ? Config["spectator_button_color"] : "0xE9E8E4"

; Error popup coordinates and color
ErrorPopupX := Config.Has("error_popup_x") ? Config["error_popup_x"] : 990
ErrorPopupY := Config.Has("error_popup_y") ? Config["error_popup_y"] : 460
ErrorPopupColor := Config.Has("error_popup_color") ? Config["error_popup_color"] : "0x262626"
ErrorPopupOKX := Config.Has("error_popup_ok_x") ? Config["error_popup_ok_x"] : 1154
ErrorPopupOKY := Config.Has("error_popup_ok_y") ? Config["error_popup_ok_y"] : 603

; Timing settings
MatchTimeout := Config.Has("match_timeout") ? Config["match_timeout"] : 180  ; seconds
WaitBetweenClicks := Config.Has("wait_between_clicks") ? Config["wait_between_clicks"] : 1500  ; milliseconds
MaxWaitForMatch := Config.Has("max_wait_for_match") ? Config["max_wait_for_match"] : 120  ; seconds to wait for match to start
ColorTolerance := Config.Has("color_tolerance") ? Config["color_tolerance"] : 20  ; tolerance for color matching

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

; Navigate to find a match with the updated UI flow
FindMatch() {
    LogMessage("Finding a match...")
    
    ; Make sure CS2 is the active window
    WinActivate "Counter-Strike"
    Sleep 2000
    
    ; 1. Press Play button
    LogMessage("Clicking Play button at coordinates: " PlayButtonX "," PlayButtonY)
    Click PlayButtonX, PlayButtonY
    Sleep WaitBetweenClicks
    
    ; 2. Select Matchmaking mode
    LogMessage("Selecting matchmaking mode at coordinates: " ModeSelectionX "," ModeSelectionY)
    Click ModeSelectionX, ModeSelectionY
    Sleep WaitBetweenClicks
    
    ; 3. Select League (Casual)
    LogMessage("Selecting casual league at coordinates: " LeagueSelectionX "," LeagueSelectionY)
    Click LeagueSelectionX, LeagueSelectionY
    Sleep WaitBetweenClicks
    
    ; 4. Select Sigma match type
    LogMessage("Selecting Sigma match type at coordinates: " SelectSigmaX "," SelectSigmaY)
    Click SelectSigmaX, SelectSigmaY
    Sleep WaitBetweenClicks
    
    ; 5. Accept/Start Match
    LogMessage("Clicking Accept Match at coordinates: " AcceptMatchX "," AcceptMatchY)
    Click AcceptMatchX, AcceptMatchY
    Sleep WaitBetweenClicks
    
    ; For debugging, take a screenshot of current state
    LogMessage("Taking screenshot of current state...")
    Send "{PrintScreen}"
    
    LogMessage("Match joining sequence completed")
    return true
}

; Function to check for color match with tolerance
IsColorSimilar(x, y, targetColor, tolerance := 20) {
    pixelColor := PixelGetColor(x, y)
    
    ; Convert hex strings to numbers if needed
    if (Type(targetColor) = "String" && SubStr(targetColor, 1, 2) = "0x")
        targetColor := Integer("0x" . SubStr(targetColor, 3))
    else if (Type(targetColor) = "String")
        targetColor := Integer("0x" . targetColor)
        
    if (Type(pixelColor) = "String" && SubStr(pixelColor, 1, 2) = "0x")
        pixelColor := Integer("0x" . SubStr(pixelColor, 3))
    else if (Type(pixelColor) = "String")
        pixelColor := Integer("0x" . pixelColor)
    
    ; Extract RGB components
    targetR := (targetColor >> 16) & 0xFF
    targetG := (targetColor >> 8) & 0xFF
    targetB := targetColor & 0xFF
    
    pixelR := (pixelColor >> 16) & 0xFF
    pixelG := (pixelColor >> 8) & 0xFF
    pixelB := pixelColor & 0xFF
    
    ; Calculate color difference
    diffR := Abs(targetR - pixelR)
    diffG := Abs(targetG - pixelG)
    diffB := Abs(targetB - pixelB)
    
    ; Check if within tolerance
    return (diffR <= tolerance) && (diffG <= tolerance) && (diffB <= tolerance)
}

; Function to check for match outcomes (success or failure)
CheckMatchOutcome() {
    LogMessage("Checking for match outcome (success or failure)...")
    
    ; Store start time to enforce timeout
    startTime := A_TickCount
    timeout := MaxWaitForMatch * 1000  ; Convert to milliseconds
    
    loop {
        ; Check if we've exceeded the timeout
        if (A_TickCount - startTime > timeout) {
            LogMessage("Timed out waiting for match outcome")
            return "timeout"
        }
        
        ; First, check if the CS2 window is still active
        if !WinActive("Counter-Strike") {
            LogMessage("CS2 window is no longer active")
            WinActivate "Counter-Strike"
            Sleep 1000
        }
        
        ; Take periodic screenshots for debugging
        if (Mod(A_Index, 10) = 0) {  ; Every 10 checks
            LogMessage("Taking detection screenshot...")
            Send "{PrintScreen}"
        }
        
        ; Check for matchmaking failure first (using improved detection)
        if (CheckForMatchmakingFailure()) {
            LogMessage("Matchmaking failure detected and handled")
            return "failure"
        }
        
        ; Get current pixel color at spectator button
        spectatorColor := PixelGetColor(SpectatorButtonX, SpectatorButtonY)
        LogMessage("Spectator button location color: " spectatorColor)
        
        ; Check for spectator button (success scenario)
        if IsColorSimilar(SpectatorButtonX, SpectatorButtonY, SpectatorButtonColor, ColorTolerance) {
            LogMessage("Detected spectator button at " SpectatorButtonX "," SpectatorButtonY)
            
            ; Click the spectator button
            LogMessage("Clicking spectator button")
            Click SpectatorButtonX, SpectatorButtonY
            Sleep 1000
            
            ; Take a screenshot after clicking
            Send "{PrintScreen}"
            
            return "success"
        }
        
        ; Check for Tab key response (scoreboard) as additional success indicator
        if (A_Index > 10) {  ; After several checks, try Tab key
            LogMessage("Checking if Tab key shows scoreboard...")
            Send "{Tab down}"
            Sleep 1000
            Send "{PrintScreen}"  ; Take screenshot with scoreboard
            Send "{Tab up}"
            Sleep 500
            
            ; This is a possible success indicator, but we'll continue checking
            ; for the spectator button to be more certain
        }
        
        ; Wait before next check
        Sleep 3000
    }
    
    return "unknown"  ; Should never reach here
}

; Function to better detect the matchmaking failure dialog
CheckForMatchmakingFailure() {
    LogMessage("Checking for matchmaking failure dialog...")
    
    ; Based on the screenshot, the error dialog has several distinct elements
    ; 1. The "OK" button - which is white text on dark background at around (877, 458)
    ; 2. The title "Matchmaking Failed" at around (642, 352)
    ; 3. The overall dark semi-transparent dialog box
    
    ; Define key coordinates to check
    titleX := 642     ; Center of "Matchmaking Failed" text 
    titleY := 352
    
    okButtonX := 877  ; Center of the "OK" button
    okButtonY := 458
    
    dialogCenterX := 642 ; Center of the dialog box
    dialogCenterY := 402
    
    ; Take a screenshot first for debugging
    Send "{PrintScreen}"
    LogMessage("Taking screenshot to analyze error dialog...")
    Sleep 500
    
    ; Check multiple points on the dialog to increase accuracy
    okButtonColor := PixelGetColor(okButtonX, okButtonY)
    titleColor := PixelGetColor(titleX, titleY)
    dialogColor := PixelGetColor(dialogCenterX, dialogCenterY)
    
    ; Log all colors for debugging
    LogMessage("OK button area color: " okButtonColor)
    LogMessage("Title area color: " titleColor)
    LogMessage("Dialog center color: " dialogColor)
    
    ; In this error dialog:
    ; - The background should be dark gray/transparent black
    ; - The OK button text is white or light gray
    ; - The title text is light gray or white
    
    ; Check for general darkness in the dialog area (dark background)
    if (IsDarkColor(dialogColor)) {
        LogMessage("Detected dark dialog background")
        
        ; Look for light text colors in OK button and title areas
        if (IsLightColor(okButtonColor) || IsLightColor(titleColor)) {
            LogMessage("Detected matchmaking failure dialog!")
            
            ; Click the OK button
            LogMessage("Clicking OK button at " okButtonX "," okButtonY)
            Click okButtonX, okButtonY
            Sleep 1000
            
            ; Take another screenshot after clicking
            Send "{PrintScreen}"
            
            return true
        }
    }
    
    return false
}

; Helper function to determine if a color is dark (like dialog background)
IsDarkColor(colorHex) {
    ; Convert hex string to number if needed
    if (Type(colorHex) = "String" && SubStr(colorHex, 1, 2) = "0x")
        color := Integer("0x" . SubStr(colorHex, 3))
    else if (Type(colorHex) = "String")
        color := Integer("0x" . colorHex)
    else
        color := colorHex
        
    ; Extract RGB values
    r := (color >> 16) & 0xFF
    g := (color >> 8) & 0xFF
    b := color & 0xFF
    
    ; Calculate brightness (common formula for perceived brightness)
    brightness := (r * 0.299 + g * 0.587 + b * 0.114)
    
    ; Return true if dark (low brightness)
    return brightness < 100
}

; Helper function to determine if a color is light (like button text)
IsLightColor(colorHex) {
    ; Convert hex string to number if needed
    if (Type(colorHex) = "String" && SubStr(colorHex, 1, 2) = "0x")
        color := Integer("0x" . SubStr(colorHex, 3))
    else if (Type(colorHex) = "String")
        color := Integer("0x" . colorHex)
    else
        color := colorHex
        
    ; Extract RGB values
    r := (color >> 16) & 0xFF
    g := (color >> 8) & 0xFF
    b := color & 0xFF
    
    ; Calculate brightness (common formula for perceived brightness)
    brightness := (r * 0.299 + g * 0.587 + b * 0.114)
    
    ; Return true if light (high brightness)
    return brightness > 160
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
    LogMessage("Spectator Button: " SpectatorButtonX "," SpectatorButtonY " (Color: " SpectatorButtonColor ")")
    LogMessage("Error Popup: " ErrorPopupX "," ErrorPopupY " (Color: " ErrorPopupColor ")")
    
    MsgBox("CS2 Automation Script Starting`n`nMake sure CS2 is already running to avoid anti-cheat issues.`n`nClick OK to continue.", "CS2 Automation", "OK")
    
    ; Check if CS2 is running
    LogMessage("Checking if CS2 is running...")
    try {
        if WinExist("Counter-Strike") {
            LogMessage("CS2 is already running. Window activated.")
            WinActivate "Counter-Strike"
            Sleep 2000
        } else {
            LogMessage("CS2 is not running. Please launch CS2 manually to avoid potential anti-cheat issues.")
            if (MsgBox("CS2 is not running. It's recommended to launch CS2 manually first to avoid anti-cheat issues.`n`nLaunch CS2 now?", "CS2 Not Running", 4) = "Yes") {
                if (!LaunchCS2()) {
                    LogMessage("Failed to launch CS2. Exiting script.")
                    return
                }
            } else {
                LogMessage("User chose not to launch CS2. Exiting script.")
                return
            }
        }
    } catch Error as e {
        LogMessage("Error checking CS2 status: " e.Message)
        ; CS2 is not running, ask if we should launch it
        if (MsgBox("CS2 is not running. It's recommended to launch CS2 manually first to avoid anti-cheat issues.`n`nLaunch CS2 now?", "CS2 Not Running", 4) = "Yes") {
            if (!LaunchCS2()) {
                LogMessage("Failed to launch CS2. Exiting script.")
                return
            }
        } else {
            LogMessage("User chose not to launch CS2. Exiting script.")
            return
        }
    }
    
    ; Try to find a match
    if (!FindMatch()) {
        LogMessage("Failed to find a match. Exiting script.")
        return
    }
    
    ; Check for match outcome (success or failure)
    matchOutcome := CheckMatchOutcome()
    LogMessage("Match outcome: " matchOutcome)
    
    if (matchOutcome = "success") {
        LogMessage("Successfully joined match!")
        
        ; View player list
        ViewPlayerList()
        
        LogMessage("Script completed successfully")
        MsgBox("Successfully joined match and viewed player list", "Success", "OK")
    } 
    else if (matchOutcome = "failure") {
        LogMessage("Failed to join match. Error popup was detected and dismissed.")
        MsgBox("Failed to join match. Error popup was detected and dismissed.", "Failure", "Icon!")
    }
    else {
        LogMessage("Match outcome unknown or timed out")
        MsgBox("Match outcome unknown or timed out.", "Timeout", "Icon!")
    }
}

; Run the main function
Main()