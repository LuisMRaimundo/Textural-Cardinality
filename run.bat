@echo off
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

python -m textural_cardinality %*

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%

