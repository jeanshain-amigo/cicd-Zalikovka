# Використовуємо офіційний образ Python як базовий
FROM python:3.13-slim

# Встановлюємо змінні середовища
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Встановлюємо робочу директорію в контейнері
WORKDIR /app

# Копіюємо файли вимог
COPY requirements.txt /app/

# Встановлюємо залежності
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Копіюємо весь проєкт у контейнер
COPY . /app/

# Налаштування прав доступу
RUN mkdir -p /app/static \
    && mkdir -p /app/media \
    && chmod -R 755 /app

# Встановлюємо PostgreSQL-клієнт (для psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Визначаємо порт, який буде використовуватись
EXPOSE 8000

# Команда для запуску сервера
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ZalikDjango2.wsgi:application"]