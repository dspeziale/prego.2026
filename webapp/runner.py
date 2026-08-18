"""Esecuzione del collector (main.py) dall'interfaccia web.

Un solo processo alla volta: l'output è raccolto in memoria e
consultabile mentre la raccolta è in corso.
"""

import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_LOG_LINES = 1000


class CollectorRunner:
    """Avvia `python main.py <date...>` e ne cattura l'output."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen] = None
        self._log: List[str] = []
        self._args: List[str] = []
        self._returncode: Optional[int] = None

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self, args: List[str]) -> bool:
        """Avvia la raccolta; False se un'altra è già in corso."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return False
            command = [sys.executable, "-u", "main.py", *args]
            logger.info("Avvio raccolta: %s", " ".join(command))
            self._log = [f"$ python main.py {' '.join(args)}".rstrip()]
            self._args = list(args)
            self._returncode = None
            self._process = subprocess.Popen(
                command,
                cwd=self._project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        threading.Thread(target=self._pump_output, daemon=True).start()
        return True

    def _pump_output(self) -> None:
        """Copia l'output del processo nel log, riga per riga."""
        process = self._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            with self._lock:
                self._log.append(line.rstrip())
                if len(self._log) > MAX_LOG_LINES:
                    del self._log[: len(self._log) - MAX_LOG_LINES]
        process.wait()
        with self._lock:
            self._returncode = process.returncode
            self._log.append(
                f"--- terminato con codice {process.returncode} ---"
            )

    def status(self) -> Dict[str, Any]:
        """Stato corrente: running, args, esito e log."""
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            return {
                "running": running,
                "args": self._args,
                "returncode": self._returncode,
                "log": "\n".join(self._log),
            }
