# Hugging Face Spaces (Docker SDK) — serves the FastAPI app on port 7860.
FROM python:3.11-slim

# System deps for trafilatura/lxml extraction.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user (HF Spaces convention: uid 1000).
RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user briefgen ./briefgen
COPY --chown=user webapp ./webapp

USER user
ENV PORT=7860
EXPOSE 7860

# Bind to 0.0.0.0 so the Space proxy can reach it.
CMD ["uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "7860"]
