@echo off
echo Running CS2 Test Server Manager....
cd /d "C:\Program Files\AutoHotkey\v2\LinkHarvester"

:: Make sure config exists
echo Checking configuration...
python config_generator.py

:: Run with admin privileges
echo Running CS2 Test Server Manager with admin privileges...
echo This will open a UAC prompt. Please approve it to allow firewall changes.
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"C:\Program Files\AutoHotkey\v2\LinkHarvester\" && python test_server_manager.py && pause' -Verb RunAs"

echo Script launched.
echo.
echo Check logs in: %USERPROFILE%\OneDrive\Документы\AutoHotkey\
echo Check data in: %USERPROFILE%\OneDrive\Документы\AutoHotkey\data\
echo.
pause