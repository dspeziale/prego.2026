"""Ricerca delle omelie sul canale YouTube @omelievangelodelgiorno.

Usa la YouTube Data API v3; la chiave si imposta in config.json
("youtube_api_key") o nella variabile d'ambiente YOUTUBE_API_KEY.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from zoneinfo import ZoneInfo
    _TZ_ROME: Optional[Any] = ZoneInfo("Europe/Rome")
except Exception:  # noqa: BLE001 - tzdata assente: si resta in UTC
    _TZ_ROME = None

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_HANDLE = "@omelievangelodelgiorno"


class YouTubeError(Exception):
    """Errore dell'API YouTube, con messaggio mostrabile all'utente."""


class YouTubeClient:
    """Client minimale per cercare video in un canale."""

    def __init__(self, api_key: str, handle: str = DEFAULT_HANDLE) -> None:
        self._api_key = (api_key or "").strip()
        self._handle = handle
        self._channel_id: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = {**params, "key": self._api_key}
        try:
            response = requests.get(
                f"{API_BASE}/{endpoint}", params=params, timeout=10
            )
        except requests.RequestException as exc:
            raise YouTubeError(f"YouTube non raggiungibile: {exc}") from exc
        data = response.json() if response.content else {}
        if response.status_code != 200:
            reason = (
                data.get("error", {}).get("message")
                or f"errore HTTP {response.status_code}"
            )
            raise YouTubeError(f"API YouTube: {reason}")
        return data

    def channel_id(self) -> str:
        """ID del canale, risolto una volta dall'handle."""
        if self._channel_id:
            return self._channel_id
        data = self._get(
            "channels", {"part": "id", "forHandle": self._handle}
        )
        items = data.get("items") or []
        if not items:
            raise YouTubeError(f"Canale {self._handle} non trovato.")
        self._channel_id = items[0]["id"]
        return self._channel_id

    def _uploads(self, pages: int = 2) -> List[Dict[str, str]]:
        """Ultimi caricamenti del canale (playlist degli upload).

        Costa 1 unità di quota a pagina, contro le 100 di search.list
        (che per alcune chiavi è inoltre vietata sui canali).
        """
        playlist_id = "UU" + self.channel_id()[2:]
        videos: List[Dict[str, str]] = []
        page_token = None
        for _ in range(pages):
            params: Dict[str, Any] = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get("playlistItems", params)
            for item in data.get("items") or []:
                snippet = item.get("snippet") or {}
                thumbnails = snippet.get("thumbnails") or {}
                thumbnail = (
                    thumbnails.get("medium") or thumbnails.get("default") or {}
                )
                videos.append({
                    "id": (snippet.get("resourceId") or {}).get("videoId", ""),
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published": (snippet.get("publishedAt") or "")[:10],
                    "thumbnail": thumbnail.get("url", ""),
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return [video for video in videos if video["id"]]

    _ACCENTS = str.maketrans("àáâèéêìíîòóôùúûÀÁÂÈÉÊÌÍÎÒÓÔÙÚÛ",
                             "aaaeeeiiiooouuuAAAEEEIIIOOOUUU")
    # articoli/preposizioni + qualifiche (grado, anno) assenti nei titoli
    _STOPWORDS = frozenset({
        "del", "della", "dei", "delle", "dello", "di", "da", "la", "il",
        "lo", "le", "gli", "un", "una", "nel", "nella", "per", "con",
        "anno", "festa", "memoria", "solennita", "facoltativa",
    })
    _RE_TOKEN = re.compile(r"[a-z0-9]+")
    _RE_ROMAN = re.compile(r"[ivxl]+")
    # separa il nucleo della celebrazione dalle qualifiche che seguono
    _RE_CORE_SPLIT = re.compile(r",|\s[–—-]\s")

    @classmethod
    def _normalize(cls, text: str) -> str:
        return text.translate(cls._ACCENTS).lower()

    @classmethod
    def _tokens(cls, text: str) -> List[str]:
        return cls._RE_TOKEN.findall(cls._normalize(text))

    @classmethod
    def _significant(cls, text: str) -> List[str]:
        """Parole della query che un titolo deve contenere.

        Scarta articoli e qualifiche; conserva i numeri romani anche
        cortissimi (II, XV...) perché distinguono la settimana.
        """
        return [
            word for word in cls._tokens(text)
            if word not in cls._STOPWORDS
            and (len(word) >= 3 or cls._RE_ROMAN.fullmatch(word))
        ]

    def _global_search(self, query: str) -> List[Dict[str, str]]:
        """search.list globale, filtrata sul canale lato client.

        Con channelId l'endpoint è vietato per alcune chiavi
        (accountDelegationForbidden): la ricerca globale invece
        raggiunge tutto il catalogo storico del canale.
        """
        data = self._get("search", {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 50,
        })
        channel = self.channel_id()
        videos = []
        for item in data.get("items") or []:
            snippet = item.get("snippet") or {}
            if snippet.get("channelId") != channel:
                continue
            thumbnails = snippet.get("thumbnails") or {}
            thumbnail = (
                thumbnails.get("medium") or thumbnails.get("default") or {}
            )
            videos.append({
                "id": item.get("id", {}).get("videoId", ""),
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published": (snippet.get("publishedAt") or "")[:10],
                "thumbnail": thumbnail.get("url", ""),
            })
        return [video for video in videos if video["id"]]

    def _matches(self, title: str, words: List[str]) -> bool:
        """Il titolo contiene tutte le parole, come parole intere.

        Il confronto per parola intera evita che XIV combaci con
        XXIV o III con VIII (succedeva con le sottostringhe).
        """
        tokens = set(self._tokens(title))
        return all(word in tokens for word in words)

    @staticmethod
    def _dedupe(videos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen: set = set()
        unique = []
        for video in videos:
            if video["id"] not in seen:
                seen.add(video["id"])
                unique.append(video)
        return unique

    def search(
        self, query: str, max_results: int = 12
    ) -> Tuple[List[Dict[str, str]], bool]:
        """Video del canale che corrispondono alla query.

        Unisce la ricerca globale (catalogo storico del canale, anche
        di anni passati) con gli ultimi upload (non ancora indicizzati
        dalla ricerca), filtra sui termini della query e ordina per
        data decrescente. Se il titolo completo non trova nulla,
        riprova con il solo nucleo della celebrazione (la parte prima
        di virgole o trattini: «San Benedetto, abate, patrono
        d'Europa – Festa» → «San Benedetto»). Restituisce
        (video, True) sulle corrispondenze; senza corrispondenze
        (upload recenti, False).
        """
        uploads = self._uploads()
        candidates = self._dedupe(self._global_search(query) + uploads)
        words = self._significant(query)
        matched = [video for video in candidates
                   if not words or self._matches(video["title"], words)]
        if not matched:
            core = self._RE_CORE_SPLIT.split(query, 1)[0].strip()
            core_words = self._significant(core)
            if core_words and core_words != words:
                candidates = self._dedupe(
                    candidates + self._global_search(core)
                )
                matched = [video for video in candidates
                           if self._matches(video["title"], core_words)]
        exact = bool(matched)
        if exact:
            # TUTTE le corrispondenze, dal più recente indietro
            # (50 = massimo arricchibile in una chiamata videos.list).
            results = sorted(
                matched, key=lambda video: video["published"], reverse=True
            )[:50]
        else:
            results = sorted(
                uploads, key=lambda video: video["published"], reverse=True
            )[:max_results]
        self._enrich(results)
        return results, exact

    _RE_DURATION = re.compile(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    )

    @classmethod
    def _format_duration(cls, iso: str) -> str:
        match = cls._RE_DURATION.fullmatch(iso or "")
        if not match:
            return ""
        hours, minutes, seconds = (int(g or 0) for g in match.groups())
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def _format_datetime(iso: str) -> str:
        try:
            moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            return iso[:10]
        if _TZ_ROME is not None:
            moment = moment.astimezone(_TZ_ROME)
        return moment.strftime("%d/%m/%Y %H:%M")

    def _enrich(self, videos: List[Dict[str, str]]) -> None:
        """Aggiunge durata e data/ora precise (videos.list, 1 unità)."""
        if not videos:
            return
        ids = ",".join(video["id"] for video in videos)
        try:
            data = self._get("videos", {
                "part": "contentDetails,snippet", "id": ids, "maxResults": 50,
            })
        except YouTubeError as exc:
            logger.warning("Dettagli video non disponibili: %s", exc)
            return
        details = {item["id"]: item for item in data.get("items") or []}
        for video in videos:
            item = details.get(video["id"])
            if not item:
                continue
            video["duration"] = self._format_duration(
                (item.get("contentDetails") or {}).get("duration", "")
            )
            published = (item.get("snippet") or {}).get("publishedAt")
            if published:
                video["published"] = self._format_datetime(published)
