FROM python:3.11-slim

WORKDIR /telegram-trade-bot

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip setuptools wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --with service --no-root

COPY . .

ENV PYTHONPATH="/telegram-trade-bot"

WORKDIR /telegram-trade-bot/service/app

EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
