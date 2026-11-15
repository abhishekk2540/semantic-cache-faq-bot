FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EMBEDDER=model

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu \
    && uv sync --system

COPY app ./app
COPY data ./data
RUN EMBEDDER=model python -c "from app.embedder import load_model; load_model()"

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
