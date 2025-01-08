import logging
from datetime import datetime
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Timeout-Konfiguration
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

async def fetch_data(
    api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None
) -> dict:
    if not isinstance(session, aiohttp.ClientSession):
        raise ValueError("Session ist ungültig oder fehlt!")
    """
    Ruft Daten von der API ab.

    Args:
        api_url (str): API-URL.
        api_parameter (dict): Anfrageparameter.
        session (aiohttp.ClientSession, optional): Bestehende Session.

    Returns:
        dict: Die empfangenen JSON-Daten oder leeres Dict bei Fehlern.
    """
    _LOGGER.debug("Sende Anfrage an API: %s mit Parametern %s", api_url, api_parameter)

    if not isinstance(api_url, str):  # Typprüfung für URL
        raise ValueError(f"Ungültige URL: {api_url}")

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
            _LOGGER.debug("API-Antwort erhalten: %s", data)
            return data
    except aiohttp.ClientResponseError as error:
        _LOGGER.error(
            "API Fehler: Status %s, Nachricht: %s, URL: %s",
            error.status,
            error.message,
            error.request_info.url,
        )
    except Exception as error:
        _LOGGER.error("Unbekannter Fehler beim API-Aufruf: %s", error)
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
    if not isinstance(json_daten, list):  # Typprüfung für Datenstruktur
        raise ValueError("Ungültige JSON-Datenstruktur erhalten.")

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

        _LOGGER.debug("JSON-Daten verarbeitet: %d Einträge", len(liste))
        return liste
    except (KeyError, ValueError, IndexError, TypeError) as error:
        _LOGGER.error("Fehler beim Verarbeiten der JSON-Daten: %s", error)
        raise RuntimeError("Ungültige JSON-Daten erhalten.") from error
