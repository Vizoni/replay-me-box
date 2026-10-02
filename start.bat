@echo off

cd /d "%~dp0"

echo Iniciando Replay Me...

start "Replay Me - Capture" cmd /k "python src\capture.py"

timeout /t 2 /nobreak > nul

start "Replay Me - Buffer" cmd /k "python src\buffer.py"

echo Replay Me iniciado.