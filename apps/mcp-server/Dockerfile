FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server /app/server

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]

ENV PYTHONUNBUFFERED=1