import os

import subprocess

from dotenv import load_dotenv

from logger import log, cleanup_old_logs

## Esse arquivo é responsável por capturar o stream RTSP e salvar os segmentos de vídeo no buffer.

load_dotenv()

BUFFER_DIR = os.getenv("BUFFER_DIR")
FFMPEG = os.getenv("FFMPEG_PATH")
RTSP_URL = os.getenv("RTSP_URL")


os.makedirs(BUFFER_DIR, exist_ok=True)

cleanup_old_logs()

log("CAPTURE", "Iniciando captura RTSP")

log("CAPTURE", "Iniciando FFmpeg para captura do stream")
result = subprocess.run([
    FFMPEG,
    "-rtsp_transport", "tcp",
    "-i", RTSP_URL,
    "-map", "0:0",
    "-c:v", "copy",
    "-f", "segment",
    "-segment_time", "1",
    "-reset_timestamps", "1",
    os.path.join(BUFFER_DIR, "segment_%03d.mp4")
])
log(
    "CAPTURE",
    f"FFmpeg encerrou com código {result.returncode}"
)