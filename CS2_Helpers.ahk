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
    configDir := "C:\LinkHarvesterScript\data"
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
            Sleep 1000
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
    Global CONFIG
    
    ; Set default paths if CONFIG doesn't have them
    cs2_path := "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe"
    steam_path := "C:\Program Files (x86)\Steam\steam.exe"
    
    ; Use CONFIG values if they exist
    if (IsObject(CONFIG) && CONFIG.HasOwnProp("cs2_executable"))
        cs2_path := CONFIG.cs2_executable
        
    if (IsObject(CONFIG) && CONFIG.HasOwnProp("steam_executable"))
        steam_path := CONFIG.steam_executable
    
    LogMessage("Attempting to launch CS2...")
    LogMessage("CS2 Executable: " cs2_path)
    
    ; Check if CS2 executable exists
    if !FileExist(cs2_path) {
        LogMessage("Error: CS2 executable not found at: " cs2_path)
        MsgBox("CS2 executable not found at: " cs2_path "`n`nPlease update the configuration file.", "Error", "Icon!")
        return false
    }
    
    ; Check if Steam is running
    If !ProcessExist("steam.exe") {
        LogMessage("Steam not running. Launching Steam...")
        LogMessage("Steam Executable: " steam_path)
        Run steam_path
        Sleep 10000  ; Wait for Steam to initialize
    }
    
    ; Launch CS2
    LogMessage("Launching CS2...")
    Run cs2_path
    
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
    Sleep 1000  ; Wait for the game to fully load
    return true
}

; Simplified screenshot function that only uses Steam's F12
CaptureScreenshot() {
    try {
        LogMessage("Taking Steam screenshot with F12")
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
        
        ; Use Run with "Hide" option and A_ComSpec
        shell := ComObject("WScript.Shell")
        exec := shell.Exec(A_ComSpec " /c python " . scriptPath . " " . command)
        
        ; Read the output
        result := exec.StdOut.ReadAll()
        LogMessage("Python detector output: " result)
        return result
    } catch Error as e {
        LogMessage("Error running Python detector: " e.Message)
        return ""
    }
}