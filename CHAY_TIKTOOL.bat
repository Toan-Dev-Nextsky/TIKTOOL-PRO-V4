@echo off
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "BB_RB.py"
) else if exist "C:\Python311\pythonw.exe" (
    start "" "C:\Python311\pythonw.exe" "BB_RB.py"
) else (
    start "" python "BB_RB.py"
)
exit
