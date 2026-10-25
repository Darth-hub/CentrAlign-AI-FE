FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
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
