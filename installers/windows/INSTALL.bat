@echo off
title Textural_Cardinality - Installer
cd /d "%~dp0"

echo.
echo Textural_Cardinality - automatic setup
echo (Python + libraries + shortcuts)
echo.
echo GitHub: https://github.com/LuisMRaimundo/Textural_Cardinality
echo.
echo Do not close this window until finished.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Easy.ps1"
set ERR=%ERRORLEVEL%

echo.
if %ERR% NEQ 0 (
  echo Installation failed. See install.log in:
  echo %LOCALAPPDATA%\Programs\Textural_Cardinality\
) else (
  echo Done.
)
echo.
pause
exit /b %ERR%
