FROM python:3.11-slim

RUN addgroup --system mlapp && adduser --system --ingroup mlapp mlapp

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ src/
# Models directory (volume-mounted in compose for persistence)
RUN mkdir -p models && chown -R mlapp:mlapp /app

USER mlapp

EXPOSE 8001

# Set PYTHONPATH so src/ modules resolve
ENV PYTHONPATH=/app/src

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]

