# service/Dockerfile

# ====== Стадия сборки (builder) ======
FROM python:3.11-slim as builder

# Устанавливаем рабочую директорию
WORKDIR /app

# Скопируем только файлы для установки зависимостей
COPY pyproject.toml poetry.lock ./

# Обновим pip, поставим Poetry
RUN pip install --upgrade pip setuptools wheel
RUN pip install poetry

# Устанавливаем зависимости только для сервиса, без самого кода (no-root)
RUN poetry install --only service --no-root

# ====== Стадия финальная (runner) ======
FROM python:3.11-slim

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/poetry /usr/local/bin/poetry

# Копируем сам проект (папку service) в контейнер
COPY service/ ./

# Пробрасываем порт 8001
EXPOSE 8001

# Команда запуска: uvicorn
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
