FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:/app/apps/attribute_extractor

WORKDIR /app

# curl: healthcheck. Java/poppler/gl: needed when INSTALL_PIPELINE=1 (OCR/dedoc).
RUN apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=120 -o Acquire::https::Timeout=120 update && \
    apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=120 -o Acquire::https::Timeout=120 install -y --no-install-recommends \
    build-essential \
    curl \
    default-jre-headless \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY apps/attribute_extractor/backend/requirements.txt ./apps/attribute_extractor/backend/requirements.txt
COPY requirements.txt ./requirements.txt

ARG INSTALL_PIPELINE=0

RUN pip install --upgrade pip --retries 10 --timeout 120 && \
    pip install -r apps/attribute_extractor/backend/requirements.txt pyyaml --retries 10 --timeout 120 && \
    if [ "$INSTALL_PIPELINE" = "1" ]; then \
      pip install -r requirements.txt --retries 10 --timeout 120 && \
      pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --retries 10 --timeout 120; \
    fi

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
