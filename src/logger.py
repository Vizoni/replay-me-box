import os
from datetime import datetime, timedelta

LOG_DIR = "logs"
LOG_RETENTION_DAYS = 15
LOG_FILE = os.path.join(LOG_DIR, "replay-me.log")

# ============================================================
# LIMPEZA DE LOGS ANTIGOS
# ============================================================

def cleanup_old_logs():

    os.makedirs(LOG_DIR, exist_ok=True)

    today = datetime.now().date()

    cutoff_date = (
        today - timedelta(days=LOG_RETENTION_DAYS)
    )

    for filename in os.listdir(LOG_DIR):

        if not filename.endswith(".log"):
            continue

        try:

            date_string = filename[:-4]

            file_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            continue

        if file_date < cutoff_date:

            filepath = os.path.join(
                LOG_DIR,
                filename
            )

            try:

                os.remove(filepath)

            except Exception as e:

                print(
                    f"[LOGGER] Não foi possível "
                    f"remover log antigo "
                    f"{filename}: {e}"
                )

def log(category, message):
    """
    Registra uma mensagem no arquivo de log com timestamp e categoria.
    """

    os.makedirs(LOG_DIR, exist_ok=True)

    now = datetime.now()

    filename = now.strftime("%Y-%m-%d.log")

    log_file = os.path.join(
        LOG_DIR,
        filename
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = (
        f"[{timestamp}] "
        f"[{category}] "
        f"{message}"
    )

    try:
        with open(
            log_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")

    except Exception as e:

        print(
            f"[LOGGER] Não foi possível gravar log: {e}"
        )