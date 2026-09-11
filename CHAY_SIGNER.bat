@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo.
echo  ========================================================
echo   TIK SIGNER PRO  -  Chuyen Ky IPA Hang Loat Theo Cert
echo   TIKTOOL PRO V4 Ecosystem
echo  ========================================================
echo.
python TIK_SIGNER.py
if errorlevel 1 (
    echo.
    echo  [LOI] Khong the chay TIK_SIGNER.py
    echo.
    pause
)
