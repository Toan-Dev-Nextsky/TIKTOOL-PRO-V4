@echo off
cd /d "%~dp0"
chcp 65001 >nul
cls

if exist "C:\Python311\python.exe" (
    "C:\Python311\python.exe" "get_udids.py"
) else (
    python "get_udids.py"
)

echo.
echo ========================================================
echo Cam tiep dot may khac va mo lai file nay de cong don!
echo ========================================================
echo.
pause
