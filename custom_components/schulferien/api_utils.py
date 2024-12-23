"""Modul zur Handhabung der API-Interaktionen für Schulferien und Feiertage."""

import logging
from datetime import datetime
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Konstante für den Timeout
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

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
            _LOGGER.debug("API-Antwort erhalten: %s", data)  # Logge die vollständige Antwort
            return data
    except aiohttp.ClientError as error:
        _LOGGER.error("Die Anfrage zur API ist fehlgeschlagen: %s", error)
        return {}
    finally:
        if close_session:
            await session.close()
            _LOGGER.debug("Die API-Session wurde geschlossen.")

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

        _LOGGER.debug("JSON-Daten erfolgreich verarbeitet: %d Einträge", len(liste))
        return liste
    except (KeyError, ValueError, IndexError, TypeError) as error:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", error)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from error