import os
import time
import subprocess
import msvcrt
import requests

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BUFFER_DIR = "buffer"
REPLAY_DIR = "replays"

# Aproximadamente 2 segundos por segmento.
# 60 segmentos = ~120 segundos de gordura.
BUFFER_SEGMENTS = 60

# Duração desejada do replay
REPLAY_SECONDS = 10

# Esperamos o stream avançar depois do botão
WAIT_AFTER_BUTTON = 5

# Depois da espera, ignoramos os segmentos mais recentes.
#
# Isso é proposital:
# queremos que o vídeo termine próximo do botão,
# e não vários segundos depois dele.
TRAILING_SECONDS = 6

CHECK_INTERVAL = 0.05

FFMPEG = os.getenv("FFMPEG_PATH")
FFPROBE = os.getenv("FFPROBE_PATH")

UPLOAD_URL = os.getenv("UPLOAD_URL")

from concurrent.futures import ThreadPoolExecutor

UPLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=2)
# ============================================================
# SEGMENTOS
# ============================================================

def get_all_segments():

    if not os.path.exists(BUFFER_DIR):
        return []

    files = [
        os.path.join(BUFFER_DIR, filename)
        for filename in os.listdir(BUFFER_DIR)
        if filename.startswith("segment_")
        and filename.endswith(".mp4")
    ]

    files.sort()

    return files


def get_segment_duration(filepath):

    try:

        result = subprocess.run(
            [
                FFPROBE,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        value = result.stdout.strip()

        if not value:
            return None

        return float(value)

    except Exception:
        return None


def get_ready_segments():

    ready = []

    for filepath in get_all_segments():

        duration = get_segment_duration(filepath)

        if duration is None:
            continue

        if duration <= 0:
            continue

        ready.append({
            "file": filepath,
            "duration": duration
        })

    return ready


# ============================================================
# LIMPEZA
# ============================================================

def cleanup_buffer():

    files = get_all_segments()

    if len(files) <= BUFFER_SEGMENTS:
        return

    for filepath in files[:-BUFFER_SEGMENTS]:

        try:
            os.remove(filepath)

        except Exception as e:

            print(
                f"[WARN] Não consegui apagar "
                f"{os.path.basename(filepath)}: {e}"
            )

def clear_buffer_on_start():
    files = get_all_segments()

    print(f"[BUFFER] Limpando {len(files)} segmentos antigos...")

    for filepath in files:
        try:
            os.remove(filepath)

        except Exception as e:
            print(
                f"[WARN] Não consegui apagar "
                f"{os.path.basename(filepath)}: {e}"
            )


# ============================================================
# UPLOAD FILE VIA ENDPOINT JAVA/SPRING PARA O AMAZON S3
# ============================================================

def upload_replay(replay_file):

    print()
    print("=" * 60)
    print("ENVIANDO REPLAY")
    print("=" * 60)

    if not os.path.exists(replay_file):

        print(
            "[ERRO] replay.mp4 não encontrado."
        )

        return

    try:

        file_size = os.path.getsize(replay_file)

        print(
            f"[UPLOAD] Arquivo: {replay_file}"
        )

        print(
            f"[UPLOAD] Tamanho: "
            f"{file_size / 1024 / 1024:.2f} MB"
        )

        print(
            f"[UPLOAD] Endpoint: {UPLOAD_URL}"
        )

        start_time = time.time()

        with open(
            replay_file,
            "rb"
        ) as file:

            response = requests.post(
                UPLOAD_URL,
                files={
                    "file": (
                        os.path.basename(replay_file),
                        file,
                        "video/mp4"
                    )
                },
                timeout=120
            )


        elapsed = time.time() - start_time

        print()

        print(
            f"[UPLOAD] HTTP {response.status_code}"
        )

        print(
            f"[UPLOAD] Tempo: {elapsed:.2f}s"
            f"[UPLOAD] Resposta: "
            f"{response.text}"
        )

        if not response.ok:

            print(
                "[UPLOAD] [ERRO] Servidor retornou erro:"
            )

            print(response.text)

            return None

        try:
            os.remove(replay_file)
            print(f"[UPLOAD] Arquivo local removido: {replay_file}")
        except Exception as e:
            print(f"[UPLOAD] Não foi possível remover arquivo local: {e}")

        data = response.json()

        print()
        print("=" * 60)
        print("REPLAY ONLINE")
        print("=" * 60)

        print(
            f"ID: {data.get('id')}"
        )

        print(
            f"Arquivo: {data.get('fileName')}"
        )

        print(
            f"Criado em: {data.get('createdAt')}"
        )

        print(
            f"URL: {data.get('url')}"
        )

        print("=" * 60)
        print()

        return data

    except requests.exceptions.ConnectionError:

        print()
        print(
            "[UPLOAD] [ERRO] "
            "Não foi possível conectar ao Spring Boot."
        )

        print(
            f"[UPLOAD] Endpoint: {UPLOAD_URL}"
        )

        return None

    except requests.exceptions.Timeout:

        print()
        print(
            "[UPLOAD] [ERRO] "
            "Upload demorou mais que 120 segundos."
        )

        return None

    except Exception as e:

        print()
        print(
            "[UPLOAD] [ERRO] "
            "Erro inesperado:"
        )

        print(e)

        return None

# ============================================================
# REPLAY
# ============================================================

def create_replay():

    from datetime import datetime

    replay_filename = (
        datetime.now().strftime(
            "replay_%Y%m%d_%H%M%S_%f.mp4"
        )
    )

    replay_file = os.path.join(REPLAY_DIR, replay_filename)

    print()
    print("=" * 60)
    print("CRIANDO REPLAY")
    print("=" * 60)

    ready_segments = get_ready_segments()

    if not ready_segments:

        print("[ERRO] Nenhum segmento pronto.")

        return

    print()
    print(
        f"[REPLAY] Segmentos disponíveis: "
        f"{len(ready_segments)}"
    )

    print(
        f"[REPLAY] Buffer aproximado: "
        f"{sum(s['duration'] for s in ready_segments):.2f}s"
    )

    print(
        f"[REPLAY] Configuração: "
        f"replay={REPLAY_SECONDS}s | "
        f"trailing={TRAILING_SECONDS}s"
    )

    # --------------------------------------------------------
    # Primeiro vamos ignorar os segmentos mais recentes.
    #
    # Exemplo:
    #
    # segmentos:
    #
    # 100 101 102 103 104 105 106
    #                         ↑
    #                     mais novo
    #
    # Se queremos ignorar ~2s:
    #
    # 100 101 102 103 104 105
    #                      ↑
    #                   termina aqui
    # --------------------------------------------------------

    ignored_duration = 0

    end_index = len(ready_segments) - 1

    while end_index > 0:

        segment = ready_segments[end_index]

        ignored_duration += segment["duration"]

        end_index -= 1

        if ignored_duration >= TRAILING_SECONDS:
            break

    print()
    print(
        f"[REPLAY] Ignorando aproximadamente "
        f"{ignored_duration:.2f}s do final do buffer."
    )

    # --------------------------------------------------------
    # Agora caminhamos para trás a partir desse ponto
    # até atingir REPLAY_SECONDS.
    # --------------------------------------------------------

    selected = []

    total_duration = 0

    for i in range(end_index, -1, -1):

        segment = ready_segments[i]

        selected.insert(0, segment)

        total_duration += segment["duration"]

        if total_duration >= REPLAY_SECONDS:
            break

    if not selected:

        print("[ERRO] Não foi possível montar replay.")

        return

    # --------------------------------------------------------
    # Mostrar segmentos
    # --------------------------------------------------------

    print()
    print("Segmentos selecionados:")

    for segment in selected:

        print(
            f"  {os.path.basename(segment['file'])}"
            f" ({segment['duration']:.2f}s)"
        )

    print()

    print(
        f"Duração aproximada: "
        f"{total_duration:.2f}s"
    )

    # --------------------------------------------------------
    # CONCAT
    # --------------------------------------------------------

    concat_file = "concat.txt"

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for segment in selected:

            filepath = (
                os.path.abspath(segment["file"])
                .replace("\\", "/")
            )

            file.write(
                f"file '{filepath}'\n"
            )

    print()
    print(
        f"[REPLAY] concat.txt criado com "
        f"{len(selected)} segmentos."
    )

    print(
        f"[REPLAY] Primeiro segmento: "
        f"{os.path.basename(selected[0]['file'])}"
    )

    print(
        f"[REPLAY] Último segmento: "
        f"{os.path.basename(selected[-1]['file'])}"
    )

    # --------------------------------------------------------
    # FFmpeg
    # --------------------------------------------------------

    print()
    print("[FFMPEG] Gerando replay...")

    command = [
        FFMPEG,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_file,
        "-c",
        "copy",
        replay_file
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print()
        print("[FFMPEG] ERRO ao gerar replay:")
        print(result.stderr)

        return

    # --------------------------------------------------------
    # Validar arquivo final
    # --------------------------------------------------------

    if not os.path.exists(replay_file):

        print(
            "[ERRO] FFmpeg terminou sem erro, "
            "mas replay.mp4 não foi encontrado."
        )

        return

    replay_size = os.path.getsize(replay_file)

    print()
    print(
        f"[FFMPEG] Replay gerado com sucesso."
    )

    print(
        f"[FFMPEG] Arquivo: {replay_file}"
    )

    print(
        f"[FFMPEG] Tamanho: "
        f"{replay_size / 1024 / 1024:.2f} MB"
    )

    print(
        f"[FFMPEG] Duração aproximada: "
        f"{total_duration:.2f}s"
    )

    print()
    print("=" * 60)
    print("REPLAY GERADO COM SUCESSO")
    print("=" * 60)
    print()

    print("[UPLOAD] Agendando upload...")

    UPLOAD_EXECUTOR.submit(upload_replay, replay_file)


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def main():

    os.makedirs(BUFFER_DIR, exist_ok=True)
    os.makedirs(REPLAY_DIR, exist_ok=True)

    print("=" * 60)
    print("VAR BUFFER B1.6")
    print("=" * 60)

    print()

    print(
        f"Buffer: {BUFFER_SEGMENTS} segmentos"
    )

    print(
        f"Replay: {REPLAY_SECONDS}s"
    )

    print(
        f"Espera após botão: {WAIT_AFTER_BUTTON}s"
    )

    print(
        f"Margem final ignorada: "
        f"{TRAILING_SECONDS}s"
    )

    print()

    print("Numpad 8 = gerar replay")
    print("Ctrl+C = sair")

    print()

    last_status = 0

    clear_buffer_on_start()

    while True:

        try:

            # ------------------------------------------------
            # Mantém o buffer continuamente
            # ------------------------------------------------

            cleanup_buffer()

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            now = time.time()

            if now - last_status >= 5:

                segments = get_all_segments()

                print(
                    f"[BUFFER] "
                    f"{len(segments)}/{BUFFER_SEGMENTS}"
                )

                last_status = now

            # ------------------------------------------------
            # Teclado
            # ------------------------------------------------

            if msvcrt.kbhit():

                key = msvcrt.getch()

                if key == b"8":

                    print()
                    print(
                        "[BOTÃO] Numpad 8 pressionado!"
                    )

                    print(
                        f"[BOTÃO] "
                        f"Aguardando "
                        f"{WAIT_AFTER_BUTTON}s..."
                    )

                    time.sleep(
                        WAIT_AFTER_BUTTON
                    )

                    print(
                        "[BOTÃO] "
                        "Montando replay..."
                    )

                    create_replay()

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print()
            print("Encerrando...")

            break

        except Exception as e:

            print()
            print("[ERRO NO LOOP]")
            print(e)

            time.sleep(1)


if __name__ == "__main__":
    main()