import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "replay-me.log")


def log(category, message):
    """
    Registra uma mensagem no arquivo de log com timestamp e categoria.
    """

    os.makedirs(LOG_DIR, exist_ok=True)

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
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")

    except Exception as e:

        print(
            f"[LOGGER] Não foi possível gravar log: {e}"
        )