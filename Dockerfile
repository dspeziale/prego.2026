# Prego: webapp Flask servita da gunicorn, per Coolify o qualsiasi Docker.
#
#   docker build -t prego .
#   docker run --rm -p 8000:8000 -e SECRET_KEY=... prego
#
# I dati (data/json, data/biennale, data/proprio, data/santi, l'APK) sono
# nell'immagine come su Vercel: si aggiornano con un nuovo deploy dopo la
# raccolta in locale e il push. Il container è in sola lettura per i dati
# (LC_READ_ONLY=1); il registro dei download può andare su un volume
# (PREGO_DOWNLOADS_LOG) e i ping dell'app su Vercel Blob (BLOB_READ_WRITE_TOKEN).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    LC_READ_ONLY=1 \
    WEB_CONCURRENCY=2 \
    PREGO_PINGS_DIR=/app/var/pings \
    PREGO_DOWNLOADS_LOG=/app/var/downloads.jsonl

WORKDIR /app

# dipendenze prima del codice: la cache di Docker le riusa a ogni deploy
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# cartella per i file di runtime (registro dei download su volume)
RUN mkdir -p /app/var && useradd --create-home --uid 10001 prego \
    && chown -R prego:prego /app/var
USER prego

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/healthz', timeout=4)" || exit 1

CMD ["sh", "-c", "exec gunicorn wsgi:app --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --threads 4 --timeout 60 --access-logfile - --error-logfile -"]
