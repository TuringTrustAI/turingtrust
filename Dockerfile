FROM python:3.11-slim

WORKDIR /app

# Install the turingtrust package with gateway extras
COPY pyproject.toml README.md ./
COPY turingtrust/ turingtrust/

RUN pip install --no-cache-dir ".[gateway]"

# Configuration via environment variables
ENV TURINGTRUST_HOST=0.0.0.0
ENV TURINGTRUST_PORT=8080
ENV TURINGTRUST_RPM=60
ENV TURINGTRUST_PII_DETECTION=true
ENV TURINGTRUST_LOGGING=true

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health').raise_for_status()"

CMD ["turingtrust-server"]
