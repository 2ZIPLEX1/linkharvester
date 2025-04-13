@echo off
echo Running CS2 Day-Aware Server Manager....
cd /d "C:\LinkHarvesterScript"

:: Make sure config exists
echo Checking configuration...
python config_generator.py

:: Make sure timezone mapping exists
echo Checking server timezone mapping...
if not exist "server_timezone_map.json" (
    echo Creating default server timezone mapping...
    python -c "import json; open('server_timezone_map.json', 'w').write(open('sample_timezone_map.json', 'r').read() if os.path.exists('sample_timezone_map.json') else '{}')"
)

:: Run with admin privileges
echo Running CS2 Day-Aware Server Manager with admin privileges...
echo This will open a UAC prompt. Please approve it to allow firewall changes.
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"C:\LinkHarvesterScript\" && python steam_server_runner.py && pause' -Verb RunAs"

echo Script launched.
echo.
echo Check logs in: C:\LinkHarvesterScript\logs
echo Check data in: C:\LinkHarvesterScript\data\
echo Check reports in: C:\LinkHarvesterScript\reports\
echo.
pause