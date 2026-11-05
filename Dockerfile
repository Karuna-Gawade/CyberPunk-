FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install foundational OS packages and Tesseract OCR with English and Hindi packs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.6 \
    pydantic==2.9.2 \
    pymupdf==1.24.10 \
    opencv-python-headless==4.10.0.84 \
    numpy==2.1.1 \
    reportlab==4.2.5 \
    pytest==8.3.3 \
    python-multipart==0.0.12

# Copy source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
