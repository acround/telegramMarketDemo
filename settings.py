import os
import sys

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit(
        "BOT_TOKEN не найден.\n"
        "В Docker нужно передать переменную окружения BOT_TOKEN:\n"
        "  docker run -e BOT_TOKEN=... ...\n"
        "или прописать её в docker-compose.yml/.env."
    )

# Параметры каталога
PAGE_SIZE = 3
