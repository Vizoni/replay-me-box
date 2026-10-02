@echo off

cd /d "%~dp0"

echo ========================================
echo          REPLAY ME - VAR BOX
echo ========================================
echo.

echo Iniciando FFmpeg...
start "Replay Me - FFmpeg" cmd /k "C:\ffmpeg\bin\ffmpeg.exe -rtsp_transport tcp -i "rtsp://bbfs:6jckaa@192.168.1.3:554/onvif1" -map 0:0 -c:v copy -f segment -segment_time 1 -reset_timestamps 1 buffer\segment_%%03d.mp4"

timeout /t 2 /nobreak > nul

echo Iniciando Python...
start "Replay Me - Python" cmd /k "python src\buffer.py"

echo.
echo Replay Me iniciado!