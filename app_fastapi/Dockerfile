# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y ffmpeg supervisor && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файл конфигурации supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Открываем необходимые порты
EXPOSE 8001 5501

# Запуск supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]