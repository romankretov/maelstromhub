FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY packages/core /app/packages/core
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

RUN pip install --no-cache-dir -e /app/packages/core -e /app/apps/api -e /app/apps/worker

WORKDIR /app/apps/worker

CMD ["python", "-m", "worker.main"]
