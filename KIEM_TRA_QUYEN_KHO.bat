@echo off
cd /d "%~dp0"
chcp 65001 >nul
cls

if exist "C:\Python311\python.exe" (
    "C:\Python311\python.exe" "KIEM_TRA_QUYEN_KHO.py" %*
) else (
    python "KIEM_TRA_QUYEN_KHO.py" %*
)

echo.
pause
