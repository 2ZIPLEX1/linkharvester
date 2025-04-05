; CS2_API_Integration_Revised.ahk
; Functions to integrate with the API service

; Leverages your existing steam_profile_manager.py for filtering
; and adds API submission capability through api_service.py

; Primary function to replace SaveProfileUrl
; This maintains compatibility with your existing code
SaveProfileUrlWithAPI(nickname, url) {
    try {
        
        ; Validate the URL
        if (!url || !InStr(url, "steamcommunity.com/")) {
            LogMessage("Invalid Steam profile URL: " url)
            return false
        }
        
        ; Extract Steam ID for logging purposes
        steamID := ""
        if (InStr(url, "/profiles/")) {
            steamIDPos := InStr(url, "/profiles/") + 10
            steamID := SubStr(url, steamIDPos)
            
            ; Remove trailing slash or other characters
            if (InStr(steamID, "/"))
                steamID := SubStr(steamID, 1, InStr(steamID, "/") - 1)
        }
        
        ; Save to CSV for our records (original behavior)
        csvPath := "C:\LinkHarvesterScript\data\player_profiles.csv"
        
        ; Create header if file doesn't exist
        if !FileExist(csvPath)
            FileAppend "Timestamp,Nickname,ProfileURL,SteamID`n", csvPath
        
        ; Format timestamp
        timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
        
        ; Sanitize nickname (remove commas)
        nickname := StrReplace(nickname, ",", "")
        
        ; Append data to CSV (now including extracted Steam ID)
        FileAppend timestamp "," nickname "," url "," steamID "`n", csvPath
        LogMessage("Saved profile URL for " nickname ": " url)
        
        ; Now, call your existing steam_bridge.py to add the URL to the queue
        ; This will use your existing SteamProfileManager logic for filtering
        ; which will eventually save to filtered_steamids.txt if it passes all checks
        ExecuteCommand("python steam_bridge.py add " . url)
        
        ; Also try to submit any filtered IDs to the API
        result := SubmitFilteredIDsToAPI()
        
        return true
    } catch Error as e {
        LogMessage("Error in SaveProfileUrlWithAPI: " e.Message)
        return false
    }
}

; Helper function to execute a command and return the output
ExecuteCommand(command) {
    try {
        shell := ComObject("WScript.Shell")
        exec := shell.Exec(A_ComSpec " /c " command)
        output := exec.StdOut.ReadAll()
        return output
    } catch Error as e {
        LogMessage("Error executing command: " e.Message)
        return ""
    }
}

; Submit filtered IDs to API
SubmitFilteredIDsToAPI() {
    try {
        LogMessage("Submitting filtered Steam IDs to API...")
        
        ; Run api_service.py to process filtered_steamids.txt
        output := ExecuteCommand("python api_service.py")
        
        ; Log the result
        LogMessage("API submission result: " output)
        
        return InStr(output, "Successfully processed") > 0
    } catch Error as e {
        LogMessage("Error submitting to API: " e.Message)
        return false
    }
}

; Function to process any saved IDs (call at startup)
ProcessSavedIDs() {
    try {
        LogMessage("Processing any previously saved Steam IDs on startup...")
        result := SubmitFilteredIDsToAPI()
        
        if (result) {
            LogMessage("Successfully processed saved IDs on startup")
        } else {
            LogMessage("No saved IDs to process or processing failed")
        }
        
        return result
    } catch Error as e {
        LogMessage("Error processing saved IDs on startup: " e.Message)
        return false
    }
}