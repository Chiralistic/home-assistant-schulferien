"""API-Hilfsfunktionen für die Schulferien-Integration."""

import logging
from datetime import datetime
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Timeout-Konfiguration
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

async def fetch_data(
    api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None
) -> dict:
    """
    Ruft Daten von der API ab.

    Args:
        api_url (str): API-URL.
        api_parameter (dict): Anfrageparameter.
        session (aiohttp.ClientSession, optional): Bestehende Session.

    Returns:
        dict: Die empfangenen JSON-Daten oder leeres Dict bei Fehlern.
    """
    if not isinstance(api_url, str) or not api_url:
        raise ValueError(f"Ungültige API-URL: {api_url}")

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
            return await response.json()
    
    except aiohttp.ClientResponseError as error:
        _LOGGER.error(
            "API Fehler: Status %s, URL: %s, Nachricht: %s",
            error.status, error.request_info.url, error.message
        )
    except aiohttp.ClientConnectionError as error:
        _LOGGER.error("Verbindungsfehler zur API: %s", error)
    except aiohttp.ClientTimeout as error:
        _LOGGER.error("API-Anfrage hat zu lange gedauert: %s", error)
    except aiohttp.ClientError as error:
        _LOGGER.error("Allgemeiner Client-Fehler beim API-Aufruf: %s", error)
    except ValueError as error:
        _LOGGER.error("Fehler beim Parsen der API-Antwort: %s", error)
    finally:
        if close_session:
            await session.close()
            _LOGGER.debug("Die API-Session wurde geschlossen.")

    return {}

def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """
    Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu.

    Args:
        json_daten (dict): JSON-Daten von der API.
        brueckentage (list, optional): Brückentage.
        typ (str): Datentyp ("ferien" oder "feiertage").

    Returns:
        list: Verarbeitete Daten.
    """
    if not isinstance(json_daten, list):
        raise ValueError("Ungültige JSON-Datenstruktur erhalten.")

    liste = []
    try:
        for eintrag in json_daten:
            if "startDate" not in eintrag or "endDate" not in eintrag:
                _LOGGER.warning("Eintrag ohne gültiges Start-/Enddatum gefunden: %s", eintrag)
                continue

            name = eintrag.get("name", [{"text": "Unbekannt"}])[0]["text"]
            liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        if typ == "ferien" and brueckentage:
            for tag in brueckentage:
                try:
                    datum = datetime.strptime(tag, "%d.%m.%Y").date()
                    liste.append({
                        "name": "Brückentag",
                        "start_datum": datum,
                        "end_datum": datum,
                    })
                except ValueError:
                    _LOGGER.warning("Ungültiges Brückentagsformat: %s", tag)

        _LOGGER.debug("JSON-Daten verarbeitet: %d Einträge", len(liste))
        return liste

    except (KeyError, ValueError, IndexError, TypeError) as error:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", error)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from error
