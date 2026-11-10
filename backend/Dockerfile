FROM python:3.11-slim

# Security: run as non-root
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini alembic.ini

RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
