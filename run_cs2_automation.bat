@echo off
echo Running CS2 Server Manager and Automation...
cd /d "%~dp0"

:: Make sure config exists
echo Generating/updating configuration...
python config_generator.py

:: Run with admin privileges
echo Running CS2 Automation with admin privileges...
echo This will open a UAC prompt. Please approve it to allow system interactions.
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"C:\Program Files\AutoHotkey\v2\AutoHotkey.exe\" CS2_Automation.ahk && pause' -Verb RunAs"

echo Script launched.
echo.
echo Check logs in: %USERPROFILE%\OneDrive\Документы\AutoHotkey\
echo Check data in: %USERPROFILE%\OneDrive\Документы\AutoHotkey\data\
echo.
pause