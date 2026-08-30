@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "LEARNING_AGENT_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%LEARNING_AGENT_PYTHON%" (
  echo Project .venv not found. Run: py -3 -m venv .venv
  echo Then run: .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)
"%LEARNING_AGENT_PYTHON%" -m backend.startup %*
set "LEARNING_AGENT_EXIT_CODE=%ERRORLEVEL%"
exit /b %LEARNING_AGENT_EXIT_CODE%
