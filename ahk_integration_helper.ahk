; CS2 Automation - Python Integration Module
; Provides functions for communicating between AHK and Python
#Requires AutoHotkey v2.0

; Include helpers
#Include "CS2_Helpers.ahk"

class PythonIntegration {
    ; Configuration for file paths
    static HARVEST_FILE := "harvest_results.json"
    static STATUS_FILE := "server_status.txt"
    
    ; Variables to track harvesting
    profilesHarvested := 0
    serverStartTime := ""
    serverName := ""
    
    ; Initialize the integration
    __New(serverName := "") {
        ; Create a timestamp for session start
        this.serverStartTime := FormatTime(, "yyyy-MM-dd HH:mm:ss")
        this.serverName := serverName
        this.profilesHarvested := 0
        
        ; Log the initialization
        LogMessage("Initialized Python integration for server: " serverName)
        LogMessage("Session started at: " this.serverStartTime)
        
        ; Signal session start to Python
        this.SignalServerStart()
    }
    
    ; Signal start of server processing
    SignalServerStart() {
        try {
            statusContent := "SERVER_STATUS=STARTED`n"
            statusContent .= "SERVER_NAME=" this.serverName "`n"
            statusContent .= "START_TIME=" this.serverStartTime "`n"
            
            FileDelete this.STATUS_FILE
            FileAppend statusContent, this.STATUS_FILE
            LogMessage("Signaled server start to Python")
            return true
        } catch Error as e {
            LogMessage("Error signaling server start: " e.Message)
            return false
        }
    }
    
    ; Increment the profile counter
    IncrementProfileCount() {
        this.profilesHarvested++
        LogMessage("Incremented profile count to: " this.profilesHarvested)
        return this.profilesHarvested
    }
    
    ; Signal completion of server processing
    SignalServerComplete() {
        try {
            ; Create a timestamp for session end
            serverEndTime := FormatTime(, "yyyy-MM-dd HH:mm:ss")
            
            ; Calculate session duration in minutes
            startTime := ParseDateTime(this.serverStartTime)
            endTime := ParseDateTime(serverEndTime)
            durationMinutes := (endTime - startTime) / 60000  ; Convert milliseconds to minutes
            
            ; Create harvest results as JSON
            harvestJson := "{"
            harvestJson .= "`"server`":`"" this.serverName "`","
            harvestJson .= "`"start_time`":`"" this.serverStartTime "`","
            harvestJson .= "`"end_time`":`"" serverEndTime "`","
            harvestJson .= "`"profiles_harvested`":" this.profilesHarvested ","
            harvestJson .= "`"duration_minutes`":" durationMinutes
            harvestJson .= "}"
            
            ; Write to file for Python to read
            FileDelete this.HARVEST_FILE
            FileAppend harvestJson, this.HARVEST_FILE
            
            ; Update status file
            statusContent := "SERVER_STATUS=COMPLETED`n"
            statusContent .= "SERVER_NAME=" this.serverName "`n"
            statusContent .= "START_TIME=" this.serverStartTime "`n"
            statusContent .= "END_TIME=" serverEndTime "`n"
            statusContent .= "PROFILES_HARVESTED=" this.profilesHarvested "`n"
            statusContent .= "DURATION_MINUTES=" durationMinutes "`n"
            
            FileDelete this.STATUS_FILE
            FileAppend statusContent, this.STATUS_FILE
            
            ; Log completion
            LogMessage("Signaled server completion to Python")
            LogMessage("Server: " this.serverName)
            LogMessage("Duration: " durationMinutes " minutes")
            LogMessage("Profiles harvested: " this.profilesHarvested)
            
            ; Also output to stdout for Python to capture directly
            OutputHarvestResults(this.serverName, this.profilesHarvested)
            
            return true
        } catch Error as e {
            LogMessage("Error signaling server completion: " e.Message)
            return false
        }
    }
}

; Helper function to parse datetime strings
ParseDateTime(datetimeStr) {
    try {
        ; Convert string to date time and return timestamp
        formatSpec := "yyyy-MM-dd HH:mm:ss"
        dt := DateParse(datetimeStr)
        return dt
    } catch Error as e {
        LogMessage("Error parsing datetime: " e.Message)
        return A_Now  ; Return current date/time as fallback
    }
}

; Date parsing function - converts string to date object
DateParse(dateString) {
    ; Handle yyyy-MM-dd HH:mm:ss format
    RegExMatch(dateString, "(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})", &match)
    
    if (match.Count >= 6) {
        ; Create a date time from components
        year := Integer(match[1])
        month := Integer(match[2])
        day := Integer(match[3])
        hour := Integer(match[4])
        min := Integer(match[5])
        sec := Integer(match[6])
        
        return DateDiff(A_NowUTC, year . month . day . hour . min . sec, "Seconds") * 1000
    }
    
    ; If couldn't parse, return current time
    LogMessage("Failed to parse date string: " dateString)
    return A_Now
}

; Function to output harvest results to stdout for Python to capture
OutputHarvestResults(server, profileCount) {
    try {
        ; Format: HARVEST_RESULT:ServerName:ProfileCount
        result := "HARVEST_RESULT:" server ":" profileCount
        
        ; Output to stdout
        FileAppend result "`n", "*"
        
        return true
    } catch Error as e {
        LogMessage("Error outputting harvest results: " e.Message)
        return false
    }
}