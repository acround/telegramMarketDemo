FROM python:3.11-slim

# Чтобы Python не буферизовал вывод (логи сразу в консоль Docker)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники бота
COPY . .

# По умолчанию база лежит в /data/store.db (мы пробросим эту папку как volume)
ENV DB_PATH=/data/store.db

# Точка входа — main.py
CMD ["python", "-u", "main.py"]
