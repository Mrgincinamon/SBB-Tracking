## SBB Tracker — Dockerfile
##
## Baut ein reproduzierbares Image fuer die Streamlit-Webapp.
## Build:  docker build -t sbb-tracker .
## Run:    docker run -p 8501:8501 --env-file .env -v ${PWD}/data:/app/data sbb-tracker
##
## Voraussetzung: .env-Datei mit ANTHROPIC_API_KEY muss vorhanden sein,
## und data/processed/ muss bereits aus Notebook 01-02 erzeugt sein
## (oder als Volume gemountet).

FROM python:3.12-slim

# Build-Tools fuer scipy/pyarrow Wheels (falls Wheel nicht passt)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies erst kopieren+installieren -> besseres Layer-Caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungs-Code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY notebooks/ ./notebooks/
COPY .env.example ./

# Streamlit erwartet diese Datei (CORS / XSRF Einstellungen)
RUN mkdir -p /root/.streamlit && \
    echo "[server]\nheadless = true\nport = 8501\naddress = \"0.0.0.0\"\nenableXsrfProtection = false\n" \
        > /root/.streamlit/config.toml

EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s \
    CMD python -c "import requests; r = requests.get('http://localhost:8501/_stcore/health'); exit(0 if r.status_code == 200 else 1)"

CMD ["streamlit", "run", "app/streamlit_app.py"]
