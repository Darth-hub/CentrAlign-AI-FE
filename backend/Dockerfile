# Pin the Debian release as well as Python; avoid silently changing apt/libc.
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# OCR uses PDFium/Pillow, not OpenCV or OpenGL. Avoid pulling Mesa/LLVM
# and other graphics libraries into a headless API/worker image.
RUN apt-get -o Acquire::Retries=3 update \
    && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --uid 10001 --create-home app && mkdir -p /data/documents && chown -R app:app /data
COPY --chown=app:app backend/ /app/backend/
COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app utilities/ /app/utilities/
USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
