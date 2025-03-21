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
    configDir := A_MyDocuments "\AutoHotkey\data"
    configFile := configDir "\config.txt"
    config := Map(
        ; Default values
        "cs2_executable", "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe",
        "steam_executable", "C:\Program Files (x86)\Steam\steam.exe",
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
        "accept_match_x", 1690,
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
    
    ; Try to load from file
    if FileExist(configFile) {
        try {
            FileContent := FileRead(configFile)
            Loop Parse, FileContent, "`n", "`r" {
                if InStr(A_LoopField, "=") {
                    parts := StrSplit(A_LoopField, "=", , 2)
                    if parts.Length = 2
                        config[Trim(parts[1])] := Trim(parts[2])
                }
            }
        } catch Error as e {
            ; Just log the error and continue with defaults
            LogMessage("Error loading configuration: " e.Message)
        }
    }
    
    ; If critical dirs don't exist, create them
    if !DirExist(configDir)
        DirCreate configDir
    
    return config
}

; Check if CS2 is running and launch it if necessary
EnsureCS2Running() {
    LogMessage("Checking if CS2 is running...")
    
    try {
        if WinExist("Counter-Strike") {
            LogMessage("CS2 is already running. Window activated.")
            WinActivate "Counter-Strike"
            Sleep 2000
            return true
        } else {
            LogMessage("CS2 is not running. Please launch CS2 manually to avoid potential anti-cheat issues.")
            if (MsgBox("CS2 is not running. It's recommended to launch CS2 manually first to avoid anti-cheat issues.`n`nLaunch CS2 now?", "CS2 Not Running", 4) = "Yes") {
                return LaunchCS2()
            } else {
                LogMessage("User chose not to launch CS2. Exiting script.")
                return false
            }
        }
    } catch Error as e {
        LogMessage("Error checking CS2 status: " e.Message)
        return false
    }
}

; Launch CS2
LaunchCS2() {
    LogMessage("Attempting to launch CS2...")
    LogMessage("CS2 Executable: " CS2_CONFIG["cs2_executable"])
    
    ; Check if CS2 executable exists
    if !FileExist(CS2_CONFIG["cs2_executable"]) {
        LogMessage("Error: CS2 executable not found at: " CS2_CONFIG["cs2_executable"])
        MsgBox("CS2 executable not found at: " CS2_CONFIG["cs2_executable"] "`n`nPlease update the configuration file.", "Error", "Icon!")
        return false
    }
    
    ; Check if Steam is running
    If !ProcessExist("steam.exe") {
        LogMessage("Steam not running. Launching Steam...")
        LogMessage("Steam Executable: " CS2_CONFIG["steam_executable"])
        Run CS2_CONFIG["steam_executable"]
        Sleep 10000  ; Wait for Steam to initialize
    }
    
    ; Launch CS2
    LogMessage("Launching CS2...")
    Run CS2_CONFIG["cs2_executable"]
    
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

; Function to take screenshots without disrupting focus
CaptureScreenshot(fileName := "") {
    try {
        if (fileName = "") {
            ; Just use PrintScreen but don't save file
            Send "{PrintScreen}"
            LogMessage("Screenshot captured to clipboard")
        } else {
            ; TODO: Implement actual file saving if needed
            LogMessage("Would save screenshot to: " fileName)
            Send "{PrintScreen}"
        }
    } catch Error as e {
        LogMessage("Error capturing screenshot: " e.Message)
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

; Take screenshots based on game's display mode

; Enhanced screenshot function that handles both fullscreen and windowed modes
CaptureFullscreenScreenshot(fileName := "") {
    try {
        ; First, try using Steam's F12 screenshot functionality (works in fullscreen)
        LogMessage("Taking Steam screenshot with F12")
        Send "{F12}"
        Sleep 500
        
        ; As a backup, also try Windows screenshot methods
        LogMessage("Also trying Windows screenshot methods")
        
        ; Method 1: Windows PrintScreen (copies to clipboard)
        Send "{PrintScreen}"
        Sleep 300
        
        ; Method 2: Win+Shift+S (opens snipping tool)
        ; Only use this as a fallback if we have a specific file to save to
        if (fileName != "") {
            LogMessage("Using Win+Shift+S for explicit screenshot capture")
            Send "#+s"  ; Win+Shift+S
            Sleep 1000
            
            ; Click fullscreen option
            Click 993, 109  ; Position of fullscreen option
            Sleep 1000
        }
    } catch Error as e {
        LogMessage("Error capturing screenshot: " e.Message)
    }
}

; Check if a file exists in Steam screenshot folder
CheckForSteamScreenshot() {
    ; Steam screenshot default location 
    steamUserID := "1067368752"  ; Your Steam User ID from the screenshot path
    screenshotDir := "C:\Program Files (x86)\Steam\userdata\" steamUserID "\760\remote\730\screenshots"
    
    try {
        if (DirExist(screenshotDir)) {
            ; Get the newest file in the directory
            Loop Files, screenshotDir "\*.jpg" {
                LogMessage("Found Steam screenshot: " A_LoopFileName)
                LogMessage("Last modified: " A_LoopFileTimeModified)
                
                ; Check if the file was created in the last minute
                fileAge := A_Now
                fileAge -= A_LoopFileTimeModified, "Seconds"  ; Correct syntax for AHK v2
                
                if (fileAge < 60) {
                    LogMessage("Recent screenshot found")
                    return A_LoopFileFullPath
                }
            }
        }
    } catch Error as e {
        LogMessage("Error checking Steam screenshots: " e.Message)
    }
    
    return ""
}