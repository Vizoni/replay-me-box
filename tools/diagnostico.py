import os
import subprocess
from datetime import datetime

BUFFER_DIR = "buffer"

FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"


def probe(filepath):
    command = [
        FFPROBE,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "frame=pts_time,pict_type",
        "-of", "csv=p=0",
        filepath
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return []

    frames = []

    for line in result.stdout.splitlines():

        parts = line.split(",")

        if len(parts) < 2:
            continue

        try:
            pts = float(parts[0])
            frame_type = parts[1]
        except ValueError:
            continue

        frames.append((pts, frame_type))

    return frames


files = [
    os.path.join(BUFFER_DIR, f)
    for f in os.listdir(BUFFER_DIR)
    if f.startswith("segment_") and f.endswith(".mp4")
]

files.sort()

# Pegar somente os últimos 10
files = files[-10:]


print()
print("=" * 100)
print("DIAGNÓSTICO DOS SEGMENTOS")
print("=" * 100)
print()


for filepath in files:

    frames = probe(filepath)

    if not frames:
        print(f"{os.path.basename(filepath)} -> SEM FRAMES")
        continue

    first_pts = frames[0][0]
    last_pts = frames[-1][0]

    keyframes = [
        pts
        for pts, frame_type in frames
        if frame_type == "I"
    ]

    first_keyframe = keyframes[0] if keyframes else None
    last_keyframe = keyframes[-1] if keyframes else None

    mtime = os.path.getmtime(filepath)

    print("-" * 100)

    print(
        f"Arquivo:       {os.path.basename(filepath)}"
    )

    print(
        f"Modificado:    "
        f"{datetime.fromtimestamp(mtime).strftime('%H:%M:%S.%f')[:-3]}"
    )

    print(
        f"Frames:        {len(frames)}"
    )

    print(
        f"PTS inicial:   {first_pts:.3f}s"
    )

    print(
        f"PTS final:     {last_pts:.3f}s"
    )

    print(
        f"Duração PTS:   {last_pts - first_pts:.3f}s"
    )

    print(
        f"Keyframe inicial: {first_keyframe}"
    )

    print(
        f"Keyframe final:   {last_keyframe}"
    )