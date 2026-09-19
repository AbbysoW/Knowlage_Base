FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY packages/kb_schemas /packages/kb_schemas
COPY packages/logger /packages/logger

COPY database/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY database/server.py .
COPY database/config.py .
COPY database/logic.py .
COPY database/data/ ./data/

EXPOSE 5432

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5432"]
