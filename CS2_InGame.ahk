; CS2 Automation - Simplified In-Game Module
; Handles actions once a match has been successfully joined

; Process the current match (view players, capture data, etc.)
ProcessMatch() {
    LogMessage("Processing match...")
    
    ; Wait a few seconds for the match to fully load
    Sleep 5000
    
    ; View the player list using Tab
    ViewPlayerList()
    
    ; Return to main menu using ESC
    ReturnToMainMenu()
    
    LogMessage("Match processing completed")
    return true
}

; View the player list using Tab
ViewPlayerList() {
    LogMessage("Viewing player list...")
    
    ; Make sure CS2 is the active window
    if !WinActive("Counter-Strike") {
        WinActivate "Counter-Strike"
        Sleep 1000
    }
    
    ; Press Tab to view scoreboard
    LogMessage("Pressing Tab to view scoreboard...")
    Send "{Tab down}"
    Sleep 2000
    
    ; Take screenshot of player list
    LogMessage("Taking screenshot of player list...")
    CaptureScreenshot()
    
    ; Release Tab
    Send "{Tab up}"
    Sleep 500
    
    return true
}

; Return to main menu using Escape key
ReturnToMainMenu() {
    LogMessage("Returning to main menu...")
    
    ; Press ESC key to open game menu
    Send "{Escape}"
    Sleep 1000
    
    ; Press ESC again to return to main menu
    Send "{Escape}"
    Sleep 2000
    
    ; Take screenshot to confirm we're back at the main menu
    CaptureScreenshot()
    
    ; Wait a bit longer for the main menu to fully load
    Sleep 3000
    
    return true
}