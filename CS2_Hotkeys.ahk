; CS2 Automation - Hotkey Handler
; Contains hotkey definitions and handling for script interruption and control

; Global flag to indicate if the script should exit
Global SCRIPT_EXIT_REQUESTED := false

; Define hotkeys
#UseHook true  ; Use the hook method for more reliable hotkey detection

; Ctrl+Alt+X - Emergency exit hotkey
^!x::EmergencyExit()

; Ctrl+Alt+P - Pause/resume script
^!p::PauseScript()

; Emergency exit function
EmergencyExit() {
    LogMessage("*** EMERGENCY EXIT TRIGGERED BY USER (Ctrl+Alt+X) ***")
    
    ; Set global flag
    SCRIPT_EXIT_REQUESTED := true
    
    ; Exit the script immediately
    ExitApp
}

; Pause/resume function
PauseScript() {
    static isPaused := false
    
    if (isPaused) {
        isPaused := false
        LogMessage("*** SCRIPT RESUMED BY USER (Ctrl+Alt+P) ***")
        Pause false  ; Unpause the script
    } else {
        isPaused := true
        LogMessage("*** SCRIPT PAUSED BY USER (Ctrl+Alt+P) ***")
        Pause true  ; Pause the script
    }
}

; Function to check if script should exit (for use in long-running loops)
ShouldExit() {
    return SCRIPT_EXIT_REQUESTED
}