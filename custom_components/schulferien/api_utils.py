"""API-Hilfsfunktionen für die Schulferien-Integration.

Zentrale Funktionen:
- fetch_data: HTTP-Abfrage der OpenHolidaysAPI mit Fallback-Logik
- parse_daten: Konvertierung der API-JSON-Response in interne Datenstruktur
- waehle_namen / sprachen_aus_liste: Namen in den gewählten Sprachen
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

    Warum session-Parameter? Der Aufrufer kann eine bestehende
    aiohttp.ClientSession durchreichen (spart Ressourcen). Ohne uebergebene
    Session wird eine neue erstellt und nach dem Aufruf wieder geschlossen.

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

# Feste Namen, die nicht von der API kommen (Brückentage aus bridge_days.yaml,
# per Gauss ergänzter Ostersonntag). Gleiche Struktur wie die API-Namen
# ({SPRACHE: Text}), damit waehle_namen sie genauso behandelt.
# Warum genau diese Sprachen? Es sind die Sprachen der translations/.
# Fehlt eine gewählte Sprache, greift der Fallback in waehle_namen (Deutsch
# zuerst = bisheriges Verhalten).
BRUECKENTAG_NAMEN = {
    "DE": "Brückentag", "EN": "Bridge Day", "NL": "Brugdag",
    "FR": "Jour de pont", "IT": "Ponte", "ES": "Puente",
    "PT": "Ponte", "DA": "Klemmedag", "TR": "Köprü Günü",
}
OSTERSONNTAG_NAMEN = {
    "DE": "Ostersonntag", "EN": "Easter Sunday", "NL": "Eerste Paasdag",
    "FR": "Dimanche de Pâques", "IT": "Domenica di Pasqua",
    "ES": "Domingo de Pascua", "PT": "Domingo de Páscoa",
    "DA": "Påskedag", "TR": "Paskalya Pazarı",
}

# Trenner bei mehreren Sprachen: "Herbstferien / Autumn Holidays"
NAMEN_TRENNER = " / "


def normalisiere_sprachen(sprachen) -> list:
    """Bringt Sprachcodes in API-Form: 2-stellig, uppercase, ohne Duplikate.

    Warum? Das Options-Formular (LanguageSelector) liefert HA-Codes wie
    "de" oder "pt-BR", die API nutzt "DE"/"PT". Die Reihenfolge bleibt
    erhalten, denn sie bestimmt die Reihenfolge im zusammengesetzten Namen.
    """
    ergebnis = []
    for sprache in sprachen or []:
        if not isinstance(sprache, str) or len(sprache) < 2:
            continue
        code = sprache[:2].upper()
        if code not in ergebnis:
            ergebnis.append(code)
    return ergebnis


def waehle_namen(namen: dict, sprachen: list) -> str:
    """Setzt den Anzeigenamen aus den gewählten Sprachen zusammen.

    Warum nicht einfach eine Sprache? Haushalte können mehrsprachig sein
    (z.B. HA auf Englisch, Kinder lesen Deutsch). Die Namen sind Daten,
    keine Frontend-Übersetzungen — jede Person sieht denselben Text, also
    müssen alle gewünschten Sprachen im Namen selbst stehen.

    - Gleiche Texte in mehreren Sprachen werden nur einmal gezeigt
      ("Pfingstferien / Pfingstferien" wäre Rauschen).
    - Hat der Eintrag keine der gewählten Sprachen, kommt der erste
      vorhandene Name — lieber eine fremde Sprache als "Unbekannt".

    Args:
        namen: {SPRACHE: Text} in API-Reihenfolge.
        sprachen: Gewählte Sprachen (API-Form, siehe normalisiere_sprachen).

    Returns:
        str: Anzeigename, "Unbekannt" nur wenn gar kein Name vorhanden ist.
    """
    texte = []
    for sprache in sprachen or []:
        text = namen.get(sprache)
        if text and text not in texte:
            texte.append(text)
    if texte:
        return NAMEN_TRENNER.join(texte)
    return next(iter(namen.values()), "Unbekannt")


def _namen_aus_eintrag(eintrag: dict) -> dict:
    """Extrahiert {SPRACHE: Text} aus dem API-Feld "name".

    Die API liefert ohne languageIsoCode alle Sprachen, z.B.
    [{"language": "DE", "text": "Herbstferien"},
     {"language": "EN", "text": "Autumn Holidays"}].
    Einträge ohne "language" (ältere Mocks/Antworten) landen unter "".
    """
    if "name" not in eintrag:
        return {}
    if not eintrag["name"]:
        # Bestandsverhalten: ein leeres name-Array gilt als kaputte Antwort
        # (parse_daten -> RuntimeError), nicht als "Unbekannt".
        raise IndexError("Leeres name-Array")
    namen = {}
    for variante in eintrag["name"]:
        sprache = str(variante.get("language") or "").upper()
        namen.setdefault(sprache, variante["text"])
    return namen


def sprachen_aus_liste(liste: list) -> list:
    """Alle Sprachen, in denen die geladenen Einträge Namen haben.

    Warum? Das Options-Formular soll nur Sprachen anbieten, die die API für
    diese Region wirklich liefert (für DE-BY: DE und EN), statt aller ~30
    Sprachen der API, von denen die meisten hier nie vorkommen.
    """
    sprachen = []
    for eintrag in liste or []:
        for sprache in eintrag.get("namen", {}):
            if sprache and sprache not in sprachen:
                sprachen.append(sprache)
    return sprachen


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


def parse_daten(json_daten, brueckentage=None, typ="ferien", sprachen=None):
    """
    Verarbeitet die JSON-Daten und fügt Brückentage oder Feiertage hinzu.

    Warum `isinstance(json_daten, list)` Check? Die API kann bei Fehlern
    ein Dict statt einer Liste zurückgeben. Dieser Check fängt das früh
    ab und wirft eine klare ValueError statt eines cryptischen KeyError.

    Args:
        json_daten (dict): JSON-Daten von der API.
        brueckentage (list, optional): Brückentage.
        typ (str): Datentyp ("ferien" oder "feiertage").
        sprachen (list, optional): Sprachen für den Anzeigenamen (API-Form,
            z.B. ["DE", "EN"]). Ohne Angabe: erster Name der API, wie bisher.

    Returns:
        list: Verarbeitete Daten. Jeder Eintrag hat "name" (Anzeigename)
        und "namen" ({SPRACHE: Text}, für das Options-Formular).
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

            # Alle Sprachvarianten behalten, Anzeigename daraus bilden
            namen = _namen_aus_eintrag(eintrag)
            liste.append({
                "name": waehle_namen(namen, sprachen),
                "namen": namen,
                "start_datum": datetime.fromisoformat(eintrag["startDate"]).date(),
                "end_datum": datetime.fromisoformat(eintrag["endDate"]).date(),
            })

        # Brückentage als zusätzliche Einträge hinzufügen
        if typ == "ferien" and brueckentage:
            for tag in brueckentage:
                try:
                    datum = datetime.strptime(tag, "%d.%m.%Y").date()
                    liste.append({
                        "name": waehle_namen(BRUECKENTAG_NAMEN, sprachen),
                        "namen": dict(BRUECKENTAG_NAMEN),
                        "name_quelle": "fest",
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
