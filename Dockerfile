# Small official Python image
FROM python:3.12-slim

# Don't write .pyc files, and show logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code and the default config
COPY uptime_pinger/ ./uptime_pinger/
COPY config.yaml .

# Run as a normal user, not root (safer)
RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["python", "-m", "uptime_pinger"]
CMD ["--config", "config.yaml"]
