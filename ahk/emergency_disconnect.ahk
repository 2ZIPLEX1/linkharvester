; Emergency Disconnect Script for CS2
; This minimal script only runs the disconnect function to exit CS2 matches
#Requires AutoHotkey v2.0

; Include only the minimal required helper file
#Include "Helpers.ahk"

; Initialize a minimal CONFIG map to prevent errors
Global CONFIG := Map(
    "cs2_executable", "D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe",
    "steam_executable", "C:\Program Files (x86)\Steam\steam.exe"
)

; Initialize logging
Global LOG_FILE := "C:\LinkHarvesterScript\logs\emergency_disconnect.log"

; Log startup
LogMessage("=== Emergency Disconnect Script Started ===")

; Run the disconnect function
EmergencyDisconnect()
ExitApp  ; Ensure the script exits when done

; Emergency disconnect function
EmergencyDisconnect() {
    try {
        LogMessage("Performing emergency disconnect from match...")
        
        ; Make sure CS2 is the active window
        activateResult := ActivateCS2Window(false)  ; Pass false to prevent relaunch attempts
        
        if (activateResult = 0) {
            ; Cannot activate window and we're not attempting relaunch
            LogMessage("CS2 window not available - emergency disconnect not needed")
            return true  ; Return success since there's no game to disconnect from
        }
        
        ; Call the disconnect function
        DisconnectFromMatch()
        
        ; Additional safety - press Escape a few times to ensure we're at the main menu
        Sleep 2000
        Send "{Escape}"
        Sleep 1000
        Send "{Escape}"
        
        LogMessage("Emergency disconnect completed")
        return true
    }
    catch Error as e {
        LogMessage("Error in emergency disconnect: " e.Message)
        return false
    }
}