"""Utenti abilitati alle modifiche (users.json alla radice del progetto).

Le password sono salvate con hash PBKDF2 (mai in chiaro). Gestione da
riga di comando:

    python users.py add <utente> <password>     aggiunge o aggiorna
    python users.py remove <utente>             rimuove
    python users.py list                        elenca
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

USERS_FILE = Path(__file__).resolve().parent.parent / "users.json"


class UserStore:
    """Verifica e gestione degli utenti su file JSON."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> Dict[str, Any]:
        if not self._path.is_file():
            return {"users": []}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("users.json non leggibile: %s", exc)
            return {"users": []}

    def _save(self, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=4)
        self._path.write_text(payload + "\n", encoding="utf-8", newline="\n")

    def verify(self, username: str, password: str) -> bool:
        """True se le credenziali corrispondono a un utente abilitato."""
        username = (username or "").strip()
        for user in self._load().get("users", []):
            if user.get("username") == username:
                return check_password_hash(
                    user.get("password_hash", ""), password or ""
                )
        return False

    def add(self, username: str, password: str) -> None:
        """Aggiunge o aggiorna un utente."""
        data = self._load()
        users: List[Dict[str, str]] = data.setdefault("users", [])
        entry = {
            "username": username.strip(),
            "password_hash": generate_password_hash(password),
        }
        for index, user in enumerate(users):
            if user.get("username") == entry["username"]:
                users[index] = entry
                break
        else:
            users.append(entry)
        self._save(data)

    def remove(self, username: str) -> bool:
        """Rimuove un utente; True se esisteva."""
        data = self._load()
        users = data.get("users", [])
        remaining = [u for u in users if u.get("username") != username]
        if len(remaining) == len(users):
            return False
        data["users"] = remaining
        self._save(data)
        return True

    def usernames(self) -> List[str]:
        return [u.get("username", "") for u in self._load().get("users", [])]


def main(argv: List[str]) -> int:
    """Gestione utenti da riga di comando."""
    store = UserStore(USERS_FILE)
    if len(argv) >= 3 and argv[0] == "add":
        store.add(argv[1], argv[2])
        print(f"Utente {argv[1]!r} salvato in {USERS_FILE}")
        return 0
    if len(argv) == 2 and argv[0] == "remove":
        print("rimosso" if store.remove(argv[1]) else "non trovato")
        return 0
    if len(argv) == 1 and argv[0] == "list":
        for name in store.usernames():
            print(name)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
