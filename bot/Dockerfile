FROM python:3.11-slim

WORKDIR /telegram-trade-bot

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip setuptools wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --with bot --no-root

COPY . .

ENV PYTHONPATH="/telegram-trade-bot"

WORKDIR /telegram-trade-bot/bot

CMD ["poetry", "run", "python", "main.py"]
