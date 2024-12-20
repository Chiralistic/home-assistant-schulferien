"""Modul zur Handhabung der API-Interaktionen für Schulferien und Feiertage."""

import json
import logging
import os
import aiohttp
import aiofiles
from datetime import datetime, timedelta
from .const import CACHE_VALIDITY_DURATION, CACHE_FILE

_LOGGER = logging.getLogger(__name__)

# Timeout für die API-Anfrage
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

async def load_cache():
    """Lädt die Cache-Daten aus der Datei, falls vorhanden und gültig."""
    if not os.path.exists(CACHE_FILE):
        return None

    async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as file:
        try:
            cache_data = json.loads(await file.read())
            timestamp = datetime.fromisoformat(cache_data.get("timestamp", ""))
            if datetime.now() - timestamp < timedelta(hours=CACHE_VALIDITY_DURATION):
                _LOGGER.debug("Gültige Cache-Daten gefunden.")
                return cache_data.get("data")
            else:
                _LOGGER.debug("Cache-Daten sind abgelaufen.")
        except (json.JSONDecodeError, ValueError) as e:
            _LOGGER.error("Fehler beim Laden des Caches: %s", e)
    return None

async def save_cache(data):
    """Speichert die Daten zusammen mit einem Zeitstempel im Cache."""
    cache_content = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    async with aiofiles.open(CACHE_FILE, "w", encoding="utf-8") as file:
        await file.write(json.dumps(cache_content))
        _LOGGER.debug("Daten wurden im Cache gespeichert.")

async def fetch_data(
    api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None
) -> dict:
    """
    Allgemeine Funktion, um Daten von der API abzurufen.

    Args:
        api_url (str): Die URL der API.
        api_parameter (dict): Die Parameter für die API-Anfrage.
        session (aiohttp.ClientSession, optional):
            Eine bestehende Session. Erstellt eine neue, wenn nicht vorhanden.

    Returns:
        dict: Die JSON-Daten von der API.

    Raises:
        aiohttp.ClientError: Bei Client-Fehlern wie Timeouts oder Verbindungsfehlern.
    """
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)

    # Versuche, den Cache zu laden
    cached_data = await load_cache()
    if cached_data:
        _LOGGER.info("Verwende Daten aus dem Cache.")
        return cached_data

    # Wenn kein gültiger Cache vorhanden ist, rufe die API ab
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        close_session = True

    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        close_session = True

    try:
        async with session.get(
            api_url,
            params=api_parameter,
            headers={"Accept": "application/json"}
        ) as response:
            response.raise_for_status()
            data = await response.json()
            #_LOGGER.debug("API-Antwort erhalten: %s", data)  # Logge die vollständige Antwort
            # Speichere die Daten im Cache
            await save_cache(data)
            return data
    except aiohttp.ClientError as error:
        #_LOGGER.error("Die Anfrage zur API ist fehlgeschlagen: %s", error)
        return {}
    finally:
        if close_session:
            await session.close()
            #_LOGGER.debug("Die API-Session wurde geschlossen.")


def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """
    Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu.

    Args:
        json_daten (dict): Die JSON-Daten von der API.
        brueckentage (list, optional): Eine Liste von Brückentagen.
        typ (str): Der Typ der Daten ("ferien" oder "feiertage").

    Returns:
        list: Eine Liste von Ferien- oder Feiertagselementen.

    Raises:
        RuntimeError: Wenn die JSON-Daten ungültig sind.
    """
    try:
        liste = []
        for eintrag in json_daten:
            name = eintrag.get("name", [{"text": "Unbekannt"}])[0]["text"]
            liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        if typ == "ferien" and brueckentage:
            for tag in brueckentage:
                datum = datetime.strptime(tag, "%d.%m.%Y").date()
                liste.append({
                    "name": "Brückentag",
                    "start_datum": datum,
                    "end_datum": datum,
                })

        #_LOGGER.debug("JSON-Daten erfolgreich verarbeitet: %d Einträge", len(liste))
        return liste
    except (KeyError, ValueError, IndexError, TypeError) as error:
        #_LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", error)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from error
