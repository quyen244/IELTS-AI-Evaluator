# The app container. It talks to Ollama over HTTP (OLLAMA_HOST) — it does NOT run
# Ollama itself. Ollama needs GPU passthrough, which is handled separately: as a
# sibling container in docker-compose.yml locally, or as a native install on the EC2
# host in deploy/aws/ec2-user-data.sh (simpler than wiring nvidia-container-toolkit
# for a one-instance demo).
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir \
    ollama pydantic pydantic-settings python-dotenv fastapi "uvicorn[standard]"

COPY src/ ./src/
COPY data/exams/ ./data/exams/
COPY __init__.py .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" || exit 1

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
