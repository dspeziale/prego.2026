"""Entry point WSGI per il deploy su Vercel.

Espone l'app Flask di LiturgiaViewer; tutte le richieste vengono
instradate qui da vercel.json.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from app import create_app  # noqa: E402  (richiede il sys.path sopra)

app = create_app()
