"""Hilfsfunktionen für die API-Abfragen in der Schulferien-Integration."""

import logging
import aiohttp
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

async def hole_daten(api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None) -> dict:
    """Allgemeine Funktion, um Daten von der API abzurufen."""
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    timeout = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

    try:
        async with session.get(
            api_url,
            params=api_parameter,
            headers={"Accept": "application/json"},
            timeout=timeout
        ) as antwort:
            antwort.raise_for_status()
            daten = await antwort.json()
            _LOGGER.debug("API-Antwort erhalten: %s", antwort.status)
            return daten
    except aiohttp.ClientTimeout as fehler:
        _LOGGER.error("Die Anfrage zur API hat das Timeout überschritten: %s", fehler)
        raise RuntimeError("API-Anfrage überschritt das Timeout-Limit.") from fehler
    except aiohttp.ClientError as fehler:
        _LOGGER.error("API-Anfrage fehlgeschlagen: %s", fehler)
        raise RuntimeError(f"API-Anfrage fehlgeschlagen: {fehler}") from fehler
    finally:
        if close_session:
            _LOGGER.debug("Die API-Session wird geschlossen.")
            await session.close()

def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu."""
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
    except (KeyError, ValueError, IndexError, TypeError) as fehler:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", fehler)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from fehler
