; CS2 Automation - Helper Functions
; Contains utility functions used across other modules

; Log a message to the log file
LogMessage(message) {
    try {
        timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
        FileAppend timestamp " - " message "`n", LOG_FILE
    } catch Error as e {
        ; If logging fails, try to create a fallback log
        try {
            fallbackLog := A_ScriptDir "\cs2_automation_fallback.log"
            FileAppend timestamp " - ERROR LOGGING: " e.Message "`n", fallbackLog
            FileAppend timestamp " - " message "`n", fallbackLog
        }
    }
}

; Load configuration from file
LoadConfiguration() {
    rootConfigFile := A_ScriptDir "\config.txt"
    dataConfigFile := "C:\LinkHarvesterScript\data\config.txt"
    
    config := Map(
        ; Default values
        "cs2_executable", "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe",
        "steam_executable", "C:\Program Files (x86)\Steam\steam.exe",
        "launch_timeout", 60,
        "max_launch_retries", 3,
        "launch_retry_delay", 5000,
        "wait_between_clicks", 1500,
        "max_wait_for_match", 120,
        "color_tolerance", 20,
        
        ; UI Coordinates
        "play_button_x", 985,
        "play_button_y", 30,
        "mode_selection_x", 813,
        "mode_selection_y", 85,
        "league_selection_x", 906,
        "league_selection_y", 130,
        "accept_match_x", 1695,
        "accept_match_y", 1030,
        
        ; Spectator button coordinates and color
        "spectator_button_x", 1592,
        "spectator_button_y", 1031,
        "spectator_button_color", "E9E8E4",
        
        ; Error popup coordinates
        "error_popup_x", 990,
        "error_popup_y", 460,
        "error_popup_ok_x", 1154,
        "error_popup_ok_y", 603
    )
    
    ; Try to load from root config file first (takes precedence)
    if FileExist(rootConfigFile) {
        try {
            LogMessage("Loading configuration from root config file: " rootConfigFile)
            FileContent := FileRead(rootConfigFile)
            LoadConfigFromContent(config, FileContent)
        } catch Error as e {
            LogMessage("Error loading root configuration: " e.Message)
        }
    }
    
    ; Then load from data directory config file for any missing settings
    if FileExist(dataConfigFile) {
        try {
            LogMessage("Loading additional configuration from data directory: " dataConfigFile)
            FileContent := FileRead(dataConfigFile)
            LoadConfigFromContent(config, FileContent)
        } catch Error as e {
            LogMessage("Error loading data directory configuration: " e.Message)
        }
    }
    
    ; If critical dirs don't exist, create them
    configDir := "C:\LinkHarvesterScript\data"
    if !DirExist(configDir)
        DirCreate configDir
    
    return config
}

; Helper function to load config values from text content
LoadConfigFromContent(config, content) {
    Loop Parse, content, "`n", "`r" {
        if InStr(A_LoopField, "=") {
            parts := StrSplit(A_LoopField, "=", , 2)
            if parts.Length = 2 {
                key := Trim(parts[1])
                value := Trim(parts[2])
                
                ; Try to convert numeric values automatically
                if RegExMatch(value, "^\d+$")
                    value := Integer(value)
                else if RegExMatch(value, "^\d+\.\d+$")
                    value := Float(value)
                ; Handle boolean values
                else if (value = "true" || value = "True")
                    value := true
                else if (value = "false" || value = "False")
                    value := false
                
                config[key] := value
                LogMessage("Loaded configuration: " key " = " value)
            }
        }
    }
    return config
}

; Find the CS2 process and return its PID (or 0 if not found)
FindCS2Process() {
    pid := ProcessExist("cs2.exe")
    if (!pid)
        pid := ProcessExist("Counter-Strike 2.exe")
    return pid
}

; Kill the CS2 process, using force if necessary
KillCS2Process() {
    pid := FindCS2Process()
    if (pid) {
        ; Try graceful termination first
        if (ProcessClose(pid)) {
            LogMessage("Successfully terminated CS2 process")
            return true
        }
        ; If graceful fails, use forced kill
        LogMessage("Attempting forced termination of CS2 process...")
        Run "taskkill /F /PID " pid
        Sleep 2000
        return !ProcessExist(pid)
    }
    return false  ; No process found to kill
}

; Check if CS2 is running and launch it if necessary
EnsureCS2Running() {
    LogMessage("Checking if CS2 is running...")
    
    try {
        if WinExist("Counter-Strike") {
            LogMessage("CS2 is already running. Window activated.")
            WinActivate "Counter-Strike"
            Sleep 1000
            
            ; Verify main menu can be reached
            if (!EnsureAtMainMenu()) {
                LogMessage("CS2 is running but main menu not accessible - restarting game")
                KillCS2Process()
                return LaunchCS2()
            }
            
            return true
        } else {
            LogMessage("CS2 is not running. Launching automatically...")
            return LaunchCS2()
        }
    } catch Error as e {
        LogMessage("Error checking CS2 status: " e.Message)
        return false
    }
}

LaunchCS2(retryCount := 0) {
    maxRetries := CONFIG.HasOwnProp("max_launch_retries") ? CONFIG["max_launch_retries"] : 3
    retryDelay := CONFIG.HasOwnProp("launch_retry_delay") ? CONFIG["launch_retry_delay"] : 5000
    launchTimeout := CONFIG.HasOwnProp("launch_timeout") ? CONFIG["launch_timeout"] : 60
    
    ; Get the game initialization wait time from config
    fullLoadWaitTime := CONFIG.HasOwnProp("cs2_load_wait_time") ? CONFIG["cs2_load_wait_time"] : 20000
    
    if (retryCount > maxRetries) {
        LogMessage("Exceeded maximum retry attempts (" maxRetries ") for launching CS2")
        return false
    }

    ; Kill any existing CS2 process that might be hung
    if (FindCS2Process()) {
        LogMessage("Found existing CS2 process before launch, terminating it")
        KillCS2Process()
        Sleep 2000  ; Give system time to clean up
    }

    ; Get Steam path from config
    steam_path := "C:\Program Files (x86)\Steam\steam.exe"
    if (IsObject(CONFIG) && CONFIG.HasOwnProp("steam_executable"))
        steam_path := CONFIG.steam_executable
    
    LogMessage("Attempting to launch CS2 via Steam protocol...")
    
    ; Check if Steam is running
    If !ProcessExist("steam.exe") {
        LogMessage("Steam not running. Launching Steam...")
        LogMessage("Steam Executable: " steam_path)
        Run steam_path
        Sleep 10000  ; Wait for Steam to initialize
    }
    
    ; Launch CS2 using Steam protocol URL
    LogMessage("Launching CS2 via steam://rungameid/730...")
    Run "steam://rungameid/730"
    
    ; Wait for CS2 to launch with the configured timeout
    try {
        WinWait "Counter-Strike", , launchTimeout
    } catch {
        LogMessage("Error: Timed out waiting for CS2 to launch after " launchTimeout " seconds")
        
        ; Check if process exists but window didn't appear (possibly hung)
        if (FindCS2Process()) {
            LogMessage("CS2 process exists but window didn't appear - killing process")
            KillCS2Process()
        }
        
        ; Retry after a delay
        LogMessage("Retrying launch (attempt " retryCount+1 " of " maxRetries ")")
        Sleep retryDelay
        return LaunchCS2(retryCount + 1)
    }
    
    ; Activate CS2 window
    WinActivate "Counter-Strike"
    LogMessage("CS2 launched and activated")
    
    ; Wait for game to fully load to main menu - no interaction during this time
    LogMessage("Waiting " fullLoadWaitTime/1000 " seconds for game to fully initialize...")
    Sleep fullLoadWaitTime
    
    ; After the full wait, do a single check for the main menu
    LogMessage("Checking if main menu is active...")
    if (EnsureAtMainMenu(2)) {  ; 2 attempts within the function
        LogMessage("CS2 successfully launched and main menu detected")
        return true
    } else {
        LogMessage("Main menu not detected after full wait - possible hang")
        KillCS2Process()
        Sleep 5000
        LogMessage("Retrying launch (attempt " retryCount+1 " of " maxRetries ")")
        return LaunchCS2(retryCount + 1)
    }
}

CaptureScreenshot() {
    try {
        LogMessage("Taking Steam screenshot")
        Send "{F12}"
        Sleep 500
        return true
    } catch Error as e {
        LogMessage("Error capturing screenshot: " e.Message)
        return false
    }
}

; Color helper functions
IsColorSimilar(x, y, targetColor, tolerance := 20) {
    try {
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
    } catch Error as e {
        LogMessage("Error in IsColorSimilar: " e.Message)
        return false
    }
}

IsDarkColor(colorHex) {
    try {
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
    } catch Error as e {
        LogMessage("Error in IsDarkColor: " e.Message)
        return false
    }
}

IsLightColor(colorHex) {
    try {
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
    } catch Error as e {
        LogMessage("Error in IsLightColor: " e.Message)
        return false
    }
}

IsRedColor(colorHex) {
    try {
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
        
        ; Check if reddish (high red value, lower green and blue)
        return (r > 180) && (r > g * 1.5) && (r > b * 1.5)
    } catch Error as e {
        LogMessage("Error in IsRedColor: " e.Message)
        return false
    }
}

IsSimilarColor(color1, color2, tolerance := 30) {
    try {
        ; Convert hex strings to numbers if needed
        if (Type(color1) = "String" && SubStr(color1, 1, 2) = "0x")
            color1 := Integer("0x" . SubStr(color1, 3))
        else if (Type(color1) = "String")
            color1 := Integer("0x" . color1)
            
        if (Type(color2) = "String" && SubStr(color2, 1, 2) = "0x")
            color2 := Integer("0x" . SubStr(color2, 3))
        else if (Type(color2) = "String")
            color2 := Integer("0x" . color2)
        
        ; Extract RGB components
        r1 := (color1 >> 16) & 0xFF
        g1 := (color1 >> 8) & 0xFF
        b1 := color1 & 0xFF
        
        r2 := (color2 >> 16) & 0xFF
        g2 := (color2 >> 8) & 0xFF
        b2 := color2 & 0xFF
        
        ; Calculate color difference
        diffR := Abs(r1 - r2)
        diffG := Abs(g1 - g2)
        diffB := Abs(b1 - b2)
        
        ; Check if within tolerance
        return (diffR <= tolerance) && (diffG <= tolerance) && (diffB <= tolerance)
    } catch Error as e {
        LogMessage("Error in IsSimilarColor: " e.Message)
        return false
    }
}

; Updated function for AHK v2
RunPythonDetector(command) {
    try {
        scriptPath := A_ScriptDir "\cs2_detect.py"
        fullCommand := A_ComSpec " /c python " . scriptPath . " " . command
        
        LogMessage("Executing command: " . fullCommand)
        
        shell := ComObject("WScript.Shell")
        exec := shell.Exec(fullCommand)
        
        ; Read stdout and stderr separately
        stdout := exec.StdOut.ReadAll()
        stderr := exec.StdErr.ReadAll()
        
        ; Log both outputs
        if (stderr)
            LogMessage("Command stderr: " . stderr)
        
        return stdout
    } catch Error as e {
        LogMessage("Error running Python detector: " e.Message)
        return ""
    }
}

; Function to check if the attention icon is visible at a specific position
IsAttentionIconVisible(x, y) {
    LogMessage("Checking for attention icon near position: " x "," y)
    
    ; Calculate ROI for attention icon (x+641, y-9 with size 31x31)
    iconRoiX := x + 641 - 15  ; Expand a bit for tolerance
    iconRoiY := y - 9 - 15    ; Expand a bit for tolerance
    iconRoiWidth := 31 + 30   ; Expand a bit for tolerance
    iconRoiHeight := 31 + 30  ; Expand a bit for tolerance
    
    ; Take a screenshot
    CaptureScreenshot()
    Sleep 800  ; Wait for screenshot to be saved
    
    ; Run Python detector
    result := RunPythonDetector("check_attention_icon " iconRoiX " " iconRoiY " " iconRoiWidth " " iconRoiHeight)
    LogMessage("Attention icon check result: " result)
    
    ; Check if icon was detected
    return InStr(result, "ATTENTION_ICON_FOUND=1")
}

; Function to clear the URL cache at the start of a new server round
ClearUrlCache() {
    LogMessage("Clearing URL cache for new server round...")
    result := RunPythonDetector("clear_url_cache")
    
    ; Parse the result for stats
    if InStr(result, "URL_CACHE_CLEARED=1") {
        clearCount := 0
        if RegExMatch(result, "CLEARED_URL_COUNT=(\d+)", &countMatch)
            clearCount := Integer(countMatch[1])
        
        LogMessage("URL cache cleared: " clearCount " URLs removed")
        return true
    } else {
        LogMessage("Failed to clear URL cache")
        return false
    }
}

; Function to clean up screenshots that are no longer needed
CleanupScreenshots() {
    try {
        screenshotsPath := "C:\Program Files (x86)\Steam\userdata\1067368752\760\remote\730\screenshots"
        thumbnailsPath := screenshotsPath "\thumbnails"
        
        ; Delete all screenshots
        LogMessage("Cleaning up CS2 screenshots...")
        FileDelete screenshotsPath "\*.jpg"
        
        ; Delete all thumbnails
        LogMessage("Cleaning up CS2 screenshot thumbnails...")
        FileDelete thumbnailsPath "\*.jpg"
        
        LogMessage("Screenshot cleanup completed")
        return true
    } catch Error as e {
        LogMessage("Error cleaning up screenshots: " e.Message)
        return false
    }
}

; Enhanced function to disconnect from match with multiple strategies
DisconnectFromMatch(maxAttempts := 3) {
    try {
        attemptCount := 0
        
        ; Try Strategy 1: Direct "Exit to main menu" button click (assuming scoreboard is visible)
        attemptCount++
        LogMessage("Disconnecting from match (strategy 1: direct exit button click)...")
        
        ; Define button coordinates
        exitButtonX := 1155
        exitButtonY := 125
        confirmYesX := 1100
        confirmYesY := 600
        
        ; Click the Exit button
        LogMessage("Clicking 'Exit to main menu' button at " exitButtonX "," exitButtonY)
        Click exitButtonX, exitButtonY
        Sleep 800
        
        ; Click the Yes confirmation button
        LogMessage("Clicking 'Yes' confirmation button at " confirmYesX "," confirmYesY)
        Click confirmYesX, confirmYesY
        Sleep 2000
        
        ; Verify if we're back in the lobby
        if VerifyBackInLobby() {
            LogMessage("Successfully disconnected using strategy 1")
            return true
        }
        
        ; Try Strategy 2: Press Escape to bring up scoreboard, then click Exit button
        if attemptCount < maxAttempts {
            attemptCount++
            LogMessage("Disconnecting from match (strategy 2: Escape key + exit button)...")
            
            ; Press Escape to bring up scoreboard
            LogMessage("Pressing Escape key to bring up scoreboard")
            Send "{Escape}"
            Sleep 1000
            
            ; Click the Exit button
            LogMessage("Clicking 'Exit to main menu' button at " exitButtonX "," exitButtonY)
            Click exitButtonX, exitButtonY
            Sleep 800
            
            ; Click the Yes confirmation button
            LogMessage("Clicking 'Yes' confirmation button at " confirmYesX "," confirmYesY)
            Click confirmYesX, confirmYesY
            Sleep 2000
            
            ; Verify if we're back in the lobby
            if VerifyBackInLobby() {
                LogMessage("Successfully disconnected using strategy 2")
                return true
            }
        }
        
        ; Try Strategy 3: Console disconnect command (fallback method)
        if attemptCount < maxAttempts {
            attemptCount++
            LogMessage("Disconnecting from match (strategy 3: console command fallback)...")
            
            ; Open console (~ key)
            LogMessage("Opening console with ~ key")
            Send "``"  ; Backtick character needs to be escaped in AHK v2
            Sleep 1000
            
            ; Type disconnect command and press Enter
            LogMessage("Entering 'disconnect' command")
            Send "disconnect{Enter}"
            Sleep 2000
            
            ; Close console
            LogMessage("Closing console")
            Send "``"
            Sleep 1000
            
            ; Verify if we're back in the lobby
            if VerifyBackInLobby() {
                LogMessage("Successfully disconnected using strategy 3 (console command)")
                return true
            }
        }
        
        ; If all strategies failed, try some last resort attempts
        LogMessage("All disconnect strategies failed, trying last resort options...")
        
        ; Try pressing Escape several times
        LogMessage("Pressing Escape key multiple times")
        Send "{Escape}"
        Sleep 800
        Send "{Escape}"
        Sleep 800
        Send "{Escape}"
        Sleep 2000
        
        ; Final verification
        if VerifyBackInLobby() {
            LogMessage("Successfully disconnected after last resort attempts")
            return true
        }
        
        LogMessage("All disconnect attempts failed")
        return false
    }
    catch Error as e {
        LogMessage("Error in DisconnectFromMatch: " e.Message)
        return false
    }
}

; Helper function to verify we're back in the lobby
VerifyBackInLobby() {
    try {
        CaptureScreenshot()
        Sleep 800
        
        ; Check for the shut-down icon in the header area of the main menu
        iconRoiX := 202  ; Approximate X coordinate of the shut-down icon
        iconRoiY := 17   ; Approximate Y coordinate of the shut-down icon
        iconRoiWidth := 31
        iconRoiHeight := 30
        
        result := RunPythonDetector("main_menu " iconRoiX " " iconRoiY " " iconRoiWidth " " iconRoiHeight)
        LogMessage("Main menu detection result: " result)
        
        return InStr(result, "MAIN_MENU_DETECTED=1")
    }
    catch Error as e {
        LogMessage("Error in VerifyBackInLobby: " e.Message)
        return false
    }
}

; Check for and dismiss voted-off error dialog
DismissVotedOffErrorDialog() {
    LogMessage("Checking for voted-off error dialog...")
    
    ; Take a screenshot
    CaptureScreenshot()
    Sleep 800  ; Wait for screenshot to be saved
    
    ; Run Python detector
    result := RunPythonDetector("check_voted_off_error_dialog")
    LogMessage("Voted-off error dialog detection result: " result)
    
    ; Check if error dialog was detected
    if InStr(result, "VOTED_OFF_ERROR_DIALOG_DETECTED=1") {
        LogMessage("Voted-off error dialog detected!")
        
        ; Try to extract coordinates from result
        if RegExMatch(result, "OK_BUTTON_COORDS=(\d+),(\d+)", &coordMatch) {
            okButtonX := Integer(coordMatch[1])
            okButtonY := Integer(coordMatch[2])
            
            LogMessage("Clicking OK button at coordinates: " okButtonX "," okButtonY)
            Click okButtonX, okButtonY
        } else {
            ; Fallback coordinates if detection didn't provide them
            LogMessage("Using fallback coordinates for OK button")
            Click 1160, 600
        }
        
        Sleep 500
        return true
    }
    
    return false
}