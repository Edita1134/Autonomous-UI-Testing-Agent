FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY agent-dashboard/requirements.txt ./dashboard-requirements.txt
RUN pip install --no-cache-dir -r dashboard-requirements.txt

COPY agent-dashboard ./agent-dashboard
COPY agent ./agent
COPY issues ./issues
COPY evidence ./evidence
COPY pyproject.toml ./pyproject.toml
COPY requirements.txt ./requirements.txt
COPY requirements-dev.txt ./requirements-dev.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV AGENT_DIR=/app
ENV AGENT_PYTHON=/usr/local/bin/python
ENV PORT=8765

WORKDIR /app/agent-dashboard
CMD ["sh", "-c", "uvicorn dashboard.app:app --host 0.0.0.0 --port ${PORT}"]
