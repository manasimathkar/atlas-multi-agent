FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run as non-root for security
RUN groupadd -r atlas && useradd -r -g atlas atlas

WORKDIR /app

# Install deps first (better caching)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# App Runner expects the app on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

USER atlas

# FastAPI app served by uvicorn — proxy-headers makes it App-Runner-friendly
CMD ["sh", "-c", "uvicorn atlas.web.server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
