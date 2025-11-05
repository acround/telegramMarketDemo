# Используем официальный образ Python
FROM python:3.11-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y     build-essential     libsqlite3-dev     && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем все файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt || true

# Устанавливаем python-telegram-bot, если не указан в requirements
RUN pip install --no-cache-dir python-telegram-bot==13.15 telebot

# Открываем порт (если нужно)
EXPOSE 8080

# Команда запуска
CMD ["python", "main.py"]