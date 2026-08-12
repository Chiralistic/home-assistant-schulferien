"""API-Hilfsfunktionen für die Schulferien-Integration.

Zentrale Funktionen:
- fetch_data: HTTP-Abfrage der OpenHolidaysAPI mit Fallback-Logik
- parse_daten: Konvertierung der API-JSON-Response in interne Datenstruktur
- load_bridge_days: Laden der Brückentage aus bridge_days.yaml
- compute_region_slug: Normalisierung von Region-Codes (DE-BY → BY)
"""

import asyncio
import logging
from datetime import datetime
import aiohttp
import aiofiles
import yaml

_LOGGER = logging.getLogger(__name__)

# Timeout-Konfiguration
# Warum 10s total, 5s connect, 5s sock_read?
# Die OpenHolidaysAPI ist normalerweise schnell (<1s). 10s total geben
# Puffer für langsame Netzwerke. Connect 5s für langsames WiFi.
# sock_read 5s für große API-Antworten (viele Feiertage).
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)

async def fetch_data(
    api_url: str, api_parameter: dict, session: aiohttp.ClientSession = None
) -> dict:
    """
    Ruft Daten von der API ab.

    Warum session-Parameter? sensor.py erstellt alle Sensoren innerhalb
    eines gemeinsamen aiohttp.ClientSession. Beide Sensoren teilen sich
    die Session für initiale Updates — spart Ressourcen.
    Wenn keine Session übergeben wird, wird eine neue erstellt und
    nach dem Aufruf wieder geschlossen.

    Args:
        api_url (str): API-URL.
        api_parameter (dict): Anfrageparameter.
        session (aiohttp.ClientSession, optional): Bestehende Session.

    Returns:
        dict: Die empfangenen JSON-Daten oder leeres Dict bei Fehlern.
    """
    # URL-Validierung — verhindert silent failures bei falschen URLs
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
            headers={"Accept": "application/json"},
        ) as response:
            response.raise_for_status()
            return await response.json()

    except aiohttp.ClientResponseError as error:
        # HTTP-Fehler (4xx, 5xx) — spezifisches Logging mit Status und URL
        _LOGGER.error(
            "API Fehler: Status %s, URL: %s, Nachricht: %s",
            error.status, error.request_info.url, error.message
        )
    except aiohttp.ClientConnectionError as error:
        # Verbindungsfehler — API nicht erreichbar (DNS, Netzwerk)
        _LOGGER.error("Verbindungsfehler zur API: %s", error)
    except asyncio.TimeoutError as error:
        # Timeout — API antwortet zu langsam
        _LOGGER.error("API-Anfrage hat zu lange gedauert: %s", error)
    except aiohttp.ClientError as error:
        # Allgemeiner Client-Fehler (unvorhergesehen)
        _LOGGER.error("Allgemeiner Client-Fehler beim API-Aufruf: %s", error)
    except ValueError as error:
        # JSON-Parse-Fehler — API antwortet mit ungültigem JSON
        _LOGGER.error("Fehler beim Parsen der API-Antwort: %s", error)
    finally:
        if close_session:
            await session.close()
            _LOGGER.debug("Die API-Session wurde geschlossen.")

    return {}


def compute_region_slug(land: str, region: str) -> str:
    """Compute a normalized region slug by stripping the country prefix.

    Strips the country prefix from region to avoid duplication
    (e.g., DE-BY -> BY) and replaces hyphens with underscores.

    Args:
        land: Country code, e.g. "DE".
        region: Region code, e.g. "DE-BY" or "BY".

    Returns:
        str: Normalized region slug, e.g. "BY".
    """
    land_upper = land.upper()
    region_raw = region if region is not None else ""
    if region_raw.startswith(land_upper + "-"):
        region_id = region_raw[len(land_upper) + 1:]
    else:
        region_id = region_raw
    return region_id.replace("-", "_")


async def load_bridge_days(bridge_days_path: str) -> list:
    """Load bridge days from a bridge_days.yaml file asynchronously.

    Warum `or {}` nach yaml.safe_load()? yaml.safe_load() gibt None
    für leere/Whitespace-only YAML-Dateien zurück. `.get("bridge_days", [])`
    auf None → AttributeError (Bug 3 Fix). `or {}` stellt sicher dass
    immer ein Dict zurückkommt.

    Args:
        bridge_days_path: Path to the YAML file.

    Returns:
        list: List of bridge days as strings (DD.MM.YYYY), empty list on error.
    """
    try:
        async with aiofiles.open(str(bridge_days_path), "r", encoding="utf-8") as file:
            content = await file.read()
            if not content:
                return []
            # `or {}` verhindert AttributeError bei leerer YAML-Datei (Bug 3 Fix)
            bridge_days_config = yaml.safe_load(content) or {}
            return bridge_days_config.get("bridge_days", [])
    except FileNotFoundError:
        _LOGGER.warning("Die Datei bridge_days.yaml wurde nicht gefunden.")
        return []
    except yaml.YAMLError as error:
        _LOGGER.error("Fehler beim Laden der Brückentage: %s", error)
        return []


def parse_daten(json_daten, brueckentage=None, typ="ferien"):
    """
    Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu.

    Warum `isinstance(json_daten, list)` Check? Die API kann bei Fehlern
    ein Dict statt einer Liste zurückgeben. Dieser Check fängt das früh
    ab und wirft eine klare ValueError statt eines cryptischen KeyError.

    Args:
        json_daten (dict): JSON-Daten von der API.
        brueckentage (list, optional): Brückentage.
        typ (str): Datentyp ("ferien" oder "feiertage").

    Returns:
        list: Verarbeitete Daten.
    """
    # API-Response muss eine Liste sein — Dict bei Fehler abfangen
    if not isinstance(json_daten, list):
        raise ValueError("Ungültige JSON-Datenstruktur erhalten.")

    liste = []
    try:
        for eintrag in json_daten:
            # Einträge ohne Start-/Enddatum überspringen (ungültige API-Daten)
            if "startDate" not in eintrag or "endDate" not in eintrag:
                _LOGGER.warning("Eintrag ohne gültiges Start-/Enddatum gefunden: %s", eintrag)
                continue

            # Lokalisierter Name extrahieren — Fallback auf "Unbekannt"
            name = eintrag.get("name", [{"text": "Unbekannt"}])[0]["text"]
            liste.append({
                "name": name,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        # Brückentage als zusätzliche Einträge hinzufügen
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
