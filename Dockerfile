FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY issues ./issues
COPY evidence ./evidence
COPY pyproject.toml .env.example ./
COPY agent-dashboard/requirements.txt ./agent-dashboard/requirements.txt
RUN pip install --no-cache-dir -r agent-dashboard/requirements.txt

COPY agent-dashboard ./agent-dashboard

ENV AGENT_DIR=/app
ENV AGENT_PYTHON=/usr/local/bin/python
ENV PORT=8765

WORKDIR /app/agent-dashboard
CMD ["sh", "-c", "uvicorn dashboard.app:app --host 0.0.0.0 --port ${PORT}"]
