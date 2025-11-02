# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем ffmpeg и системные зависимости
RUN apt-get update && apt-get install -y ffmpeg libglib2.0-0 libsm6 libxext6 git && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt requirements.txt

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Запускаем бота
CMD ["python", "bot_sticker_maker.py"]
