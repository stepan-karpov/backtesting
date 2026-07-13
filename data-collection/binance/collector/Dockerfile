FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Создаём папку для данных (будет переопределена volume)
RUN mkdir -p /data

# Переменная окружения для пути к данным
ENV DATA_ROOT=/data

# Entrypoint скрипт
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
