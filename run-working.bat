@echo off
echo Running CS2 Server Manager...
cd /d "C:\Program Files\AutoHotkey\v2\LinkHarvester"

:: Generate configuration first
echo Generating configuration...
python config_generator.py

:: Run with admin privileges using the method that worked in our test
echo Running CS2 Server Manager with admin privileges...
echo This will open a UAC prompt. Please approve it.
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"C:\Program Files\AutoHotkey\v2\LinkHarvester\" && python server_manager.py && pause' -Verb RunAs"

echo Script launched.
echo.
echo Check logs in: C:\Users\vania\OneDrive\Документы\AutoHotkey\
echo Check data in: C:\Users\vania\OneDrive\Документы\AutoHotkey\data\
echo.
pause