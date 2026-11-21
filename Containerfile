FROM docker.io/library/python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLLAMA_URL=http://host.containers.internal:11434 \
    OLLAMA_MODEL=qwen3:4b
COPY documents/ ./documents/
COPY src/ ./src/
COPY tests/ ./tests/
COPY requirements.txt ./requirements.txt
CMD ["python", "src/main.py"]
