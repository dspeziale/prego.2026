"""Entry point WSGI per i deploy in container (Coolify, Docker, gunicorn).

    gunicorn wsgi:app

Stesso wiring di api/index.py (Vercel): la webapp non è un package, quindi
la sua cartella va aggiunta a sys.path prima dell'import.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "webapp"))

from app import create_app  # noqa: E402  (richiede il sys.path sopra)

app = create_app()
