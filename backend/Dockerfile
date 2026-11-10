FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root application user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --home /app appuser

WORKDIR /app

# Install dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application and migration code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
