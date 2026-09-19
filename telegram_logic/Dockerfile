FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY packages/kb_schemas /packages/kb_schemas
COPY packages/logger /packages/logger

COPY telegram_logic/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_logic/bot.py .
COPY telegram_logic/config.py .
COPY telegram_logic/router.py .
COPY telegram_logic/modules/ ./modules/

CMD ["python", "bot.py"]