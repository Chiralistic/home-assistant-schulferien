"""Modul für die Verwaltung und den Abruf von Feiertagen.

Zwei Sensor-Klassen:
1. FeiertagSensor — Hauptsensor mit API-Abfrage
2. FeiertagMorgenSensor — Spiegel-Sensor für morgen (liest vom Hauptsensor)

Warum Ostersonntag-Ergaenzung? Die OpenHolidaysAPI liefert Ostermontag,
aber nicht immer Ostersonntag. Da Ostersonntag ein wichtiger Referenztag
ist (beginnt das Osterfest), wird er automatisch per Gauss-Formel ergänzt
— sprachunabhängig, je Jahr im Abruf-Fenster."""

import logging
from datetime import date, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.util import dt as dt_util
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT, compute_region_slug
from .const import (
    API_URL_FEIERTAGE,
    API_FALLBACK_FEIERTAGE,
    DAILY_UPDATE_HOUR,
    DAILY_UPDATE_MINUTE,
    MIDNIGHT_REFRESH_HOUR,
    MIDNIGHT_REFRESH_MINUTE,
    MIDNIGHT_REFRESH_SECOND
)

_LOGGER = logging.getLogger(__name__)

# EntityDescription mit Übersetzungsschlüssel für Home Assistant UI
FEIERTAG_SENSOR = SensorEntityDescription(
    key="feiertag",
    name="Feiertag",
    translation_key="feiertag",
)

FEIERTAG_MORGEN_SENSOR = SensorEntityDescription(
    key="feiertag_morgen",
    name="Feiertag Morgen",
    translation_key="feiertag_morgen",
)


def berechne_ostersonntag(jahr: int) -> date:
    """Berechnet Ostersonntag fuer ein Jahr (Gauss'sche Osterformel).

    Warum Gauss statt Namens-Match? Die OpenHolidaysAPI liefert Ostermontag
    unter beliebigen Sprach-Labels — der fruehere Match erkannte nur
    DE/EN-Namen und Ostersonntag fehlte bei anderen Sprachen. Gauss ist eine
    geschlossene Form: sprachunabhaengig, kein Tages-Loop, O(1) pro Jahr.

    Args:
        jahr: Das Jahr (z.B. 2024).

    Returns:
        date: Das Osterdatum (Ostersonntag) des Jahres.
    """
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = (19 * a + b - b // 4 - (b - (b + 8) // 25 + 1) // 3 + 15) % 30
    e = (2 * (b % 4) + 2 * (c // 4) - d - (c % 4) + 32) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    return date(jahr, f // 31, (f % 31) + 1)


class FeiertagSensor(SensorEntity):
    """Sensor für Feiertage.

    Hauptverantwortlichkeiten:
    - API-Abfrage der Feiertagsdaten (OpenHolidaysAPI)
    - Berechnung ob heute ein Feiertag ist
    - Angabe des nächsten Feiertags (Name, Datum)
    - Ostersonntag-Ergaenzung: wird automatisch per Gauss-Formel ergänzt (sprachunabhaengig)

    Warum 30 Tage zurück + 365 Tage vor? Gleiche Strategie wie bei Schulferien:
    30 Tage Puffer für nachgelieferte Daten, 365 Tage für Vorhersage.
    """

    def __init__(self, _hass, config):
        """Initialisiert den Feiertag-Sensor mit Konfigurationsdaten."""
        self.entity_description = FEIERTAG_SENSOR
        self._name = config["name"]
        land_upper = config["land"].upper()
        region_slug = compute_region_slug(config["land"], config["region"])
        land_lower = config["land"].lower()
        region_slug_lower = region_slug.lower()
        self._unique_id = config.get(
            "unique_id", f"feiertag_{land_upper}_{region_slug}"
        )
        # Vorgeschlagene Entity-ID (ohne Domain-Praefix): HA leitet daraus
        # z.B. "feiertag_de_rp" -> sensor.feiertag_de_rp ab.
        # Warum nicht entity_id direkt setzen? HA weist entity_id beim Add
        # selbst zu (EntityPlatform._async_add_entity). Eine eigene Property
        # ohne Setter liesse diese Zuweisung mit AttributeError crashen und
        # die Entity waere permanent "nicht verfuegbar" (Bugfix Branch 24).
        self._suggested_object_id = f"feiertag_{land_lower}_{region_slug_lower}"
        self._location = {
            "land": config["land"],
            "region": config["region"],
            "land_name": config["land_name"],
            "region_name": config["region_name"],
            # iso_code wird in async_added_to_hass aus HA konfiguriert
            "iso_code": "DE",
        }
        # Cancel-Funktion fuer den taeglichen Timer (gesetzt in async_added_to_hass)
        self._cancel_timer = None
        # Cancel-Funktion fuer den Mitternachts-State-Recompute (async_added_to_hass)
        self._cancel_midnight = None
        # Alle Feiertagsdaten und Berechnungen
        self._feiertags_info = {
            "heute_feiertag": None,
            "naechster_feiertag_name": None,
            "naechster_feiertag_datum": None,
            "feiertage_liste": [],
            "letztes_update": None,
            "letzter_versuch": None,
        }

        _LOGGER.debug(
            "FeiertagSensor initialisiert: Land=%s, Region=%s",
            self._location["land"], self._location["region"]
        )

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird."""
        _LOGGER.debug("Feiertag-Sensor hinzugefügt, erstes Update wird ausgeführt.")
        if self.hass and self.hass.config:
            self._location["iso_code"] = self.hass.config.language[:2].upper()
        else:
            self._location["iso_code"] = "DE"  # Standardwert
            _LOGGER.warning("Feiertag-Sensor: Fallback auf Standard 'DE'.")

        _LOGGER.debug("Feiertag-Sensor: Verwendeter Sprachcode: %s", self._location["iso_code"])

        letztes_update = self._feiertags_info.get("letztes_update")
        jetzt = dt_util.now()

        # Update nur bei fehlendem oder abgelaufenem (Tag gewechselt)
        if not letztes_update or letztes_update.date() != jetzt.date():
            await self.async_update()
            self.async_write_ha_state()

        async def async_daily_update(_):
            """Tägliche Aktualisierung um 03:00 Uhr."""
            _LOGGER.debug("Tägliches Update ausgelöst.")
            await self.async_update()
            self.async_write_ha_state()

        self._cancel_timer = async_track_time_change(
            self.hass,
            async_daily_update,
            hour=DAILY_UPDATE_HOUR,
            minute=DAILY_UPDATE_MINUTE,
        )
        _LOGGER.debug(
            "Tägliche Abfrage um %02d:%02d eingerichtet.", DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE
        )

        # Mitternachts-Recompute: publiziert native_value neu, sobald der Tag
        # wechselt. Kein API-Abruf — der Fetch bleibt beim wöchentlichen Guard.
        # native_value ist datumssensitiv, deshalb genügt async_write_ha_state().
        # second=0 -> genau ein Fire pro Tag (siehe MIDNIGHT_REFRESH_* in const).
        async def async_midnight_refresh(_):
            """State um Mitternacht neu schreiben, ohne die API anzurufen."""
            _LOGGER.debug("Mitternachts-Recompute: State wird neu publiziert.")
            self.async_write_ha_state()

        self._cancel_midnight = async_track_time_change(
            self.hass,
            async_midnight_refresh,
            hour=MIDNIGHT_REFRESH_HOUR,
            minute=MIDNIGHT_REFRESH_MINUTE,
            second=MIDNIGHT_REFRESH_SECOND,
        )

    async def async_will_remove_from_hass(self):
        """Cleanup: Entfernt den taeglichen Timer-Listener.
        Warum wichtig? Ohne Cleanup feuert der Listener weiter,
        nachdem die Entity aus HA entfernt wurde (z.B. bei Multi-Instance-Unload).
        """
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None
        if self._cancel_midnight:
            self._cancel_midnight()
            self._cancel_midnight = None
        _LOGGER.debug("Timer-Cleanup fuer FeiertagSensor durchgefuehrt.")

    @property
    def name(self):
        """Gibt den Namen des Sensors zurück."""
        return self._name

    @property
    def unique_id(self):
        """Gibt die eindeutige ID des Sensors zurück."""
        return self._unique_id

    @property
    def suggested_object_id(self):
        """Gibt die vorgeschlagene Entity-ID ohne Domain-Praefix zurück.

        Warum ueberschreiben? HA leitet die Entity-ID aus suggested_object_id
        ab ("feiertag_de_rp" -> sensor.feiertag_de_rp) und weist entity_id
        selbst zu. Eine eigene entity_id-Property wuerde diese Zuweisung
        blockieren (Getter-only-Property ohne Setter -> Entity
        "nicht verfuegbar").
        """
        return self._suggested_object_id

    @property
    def native_value(self):
        """Gibt den aktuellen Zustand des Sensors zurück.

        Warum dynamisch gegen das heutige Datum statt über die beim Fetch
        gesetzte 'heute_feiertag'-Flag? Der Fetch-Guard begrenzt API-Abrufe auf
        ~wöchentlich. Endet ein Feiertag, bliebe die Flag bis zum nächsten Abruf
        True. Die Prüfung gegen feiertage_liste stimmt bei jedem Lesen mit dem
        aktuellen Datum überein — ohne API-Aufruf.
        """
        heute = dt_util.now().date()
        for feiertag in self._feiertags_info.get("feiertage_liste") or []:
            if feiertag["start_datum"] <= heute <= feiertag["end_datum"]:
                return "feiertag"
        return "kein_feiertag"

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        heute = dt_util.now().date()
        aktueller_feiertag = None
        datum = None

        # Leere Liste als Fallback falls 'feiertage_liste' fehlt
        feiertage_liste = self._feiertags_info.get("feiertage_liste", [])
        for feiertag in feiertage_liste:
            if feiertag["start_datum"] == heute:
                aktueller_feiertag = feiertag["name"]
                datum = feiertag["start_datum"].strftime("%d.%m.%Y")
                break

        if not aktueller_feiertag:
            aktueller_feiertag = self._feiertags_info["naechster_feiertag_name"]
            datum = self._feiertags_info["naechster_feiertag_datum"]

        return {
            "Name Feiertag": aktueller_feiertag,
            "Datum": datum,
            "Land": self._location["land_name"],
            "Region": self._location["region_name"],
        }

    async def async_update(self, session=None):
        """Aktualisiert die Feiertagsdaten durch Abfrage der API.

        Der 3-Regel-Guard in _update_faellig begrenzt API-Abrufe auf
        1x/Tag bei Fehlschlag und 1 Woche nach Erfolg (jeweils ab 03:00).
        Der session-Parameter bleibt fuer Vertrag + Tests: Ohne uebergebene
        Session wird eine eigene erstellt und nach dem Aufruf geschlossen.
        """
        jetzt = dt_util.now()
        heute = jetzt.date()

        if not self._update_faellig(jetzt):
            _LOGGER.debug("Update übersprungen (Guard): kein Abruf fällig.")
            return

        _LOGGER.debug("Starte API-Abfrage für Feiertagsdaten.")
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
            close_session = True

        try:
            api_parameter = self.get_api_parameter(heute)
            feiertage_daten = await self.hole_feiertags_daten(api_parameter, session)

            if not feiertage_daten:
                _LOGGER.warning("Keine Daten von der API erhalten.")
                return

            self.verarbeite_feiertags_daten(feiertage_daten, heute)

            # Erfolgs-Zeitstempel NACH der Verarbeitung (Spiegel zu Schulferien):
            # garantiert letztes_update >= letzter_versuch — die Ordnung ist der
            # Fehlschlags-Beweis fuer Guard-Regel (c).
            self._feiertags_info["letztes_update"] = dt_util.now()
            _LOGGER.debug(
                "Update abgeschlossen. Neues letztes Update: %s",
                self._feiertags_info["letztes_update"],
            )

        # pylint: disable=broad-exception-caught
        except Exception as e:
            _LOGGER.error("Unerwarteter Fehler beim Aktualisieren der Feiertagsdaten: %s", e)
        # pylint: enable=broad-exception-caught

        finally:
            if close_session:
                await session.close()
                _LOGGER.debug("API-Session geschlossen.")

    def _update_faellig(self, jetzt):
        """3-Regel-Guard: entscheidet, ob ein API-Abruf jetzt faellig ist.

        Spiegel von SchulferienSensor._update_faellig — identische Regeln:
        (a) nie gefetcht + heute kein Versuch, (b) >= 7 Tage + >= 03:00,
        (c) Fehlschlag gestern + >= 03:00. Fehlschlags-Beweis ist die
        Ordnung letzter_versuch > letztes_update.
        """
        letztes_update = self._feiertags_info.get("letztes_update")
        letzter_versuch = self._feiertags_info.get("letzter_versuch")
        heute = jetzt.date()
        nach_drei_uhr = (jetzt.hour, jetzt.minute) >= (DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE)

        if letztes_update is None:
            return letzter_versuch is None or letzter_versuch.date() != heute

        if (heute - letztes_update.date()).days >= 7:
            return nach_drei_uhr

        return (
            letzter_versuch is not None
            and letzter_versuch.date() == heute - timedelta(days=1)
            and letzter_versuch > letztes_update
            and nach_drei_uhr
        )

    def get_api_parameter(self, heute):
        """Erstellt die API-Parameter für die Feiertagsanfrage."""
        return {
            "countryIsoCode": self._location["land"],
            "subdivisionCode": self._location["region"],
            "validFrom": (heute - timedelta(days=30)).strftime("%Y-%m-%d"),
            "validTo": (heute + timedelta(days=365)).strftime("%Y-%m-%d"),
            "languageIsoCode": self._location["iso_code"],
        }

    async def hole_feiertags_daten(self, api_parameter, session):
        """Versucht, die Feiertagsdaten von der API abzurufen.

        Warum letzter_versuch hier setzen? Der Versuchs-Zeitstempel muss VOR
        dem Request stehen (Guard-Regel c): Ein Fehlschlag laesst ihn liegen
        (letzter_versuch > letztes_update = Fehlschlag), ein Erfolg
        ueberschreibt letztes_update mit einem Zeitstempel >= dem Versuch.
        """
        self._feiertags_info["letzter_versuch"] = dt_util.now()
        for url in [API_URL_FEIERTAGE, API_FALLBACK_FEIERTAGE]:
            _LOGGER.debug("Prüfe URL: %s", url)
            if not isinstance(url, str):
                _LOGGER.error("Ungültige URL: %s", url)
                continue

            try:
                feiertage_daten = await fetch_data(url, api_parameter, session)
                if feiertage_daten:
                    return feiertage_daten
            except (aiohttp.ClientError, ValueError) as e:
                _LOGGER.error("Fehler beim Abrufen der Daten von %s: %s", url, e)
        return None

    def verarbeite_feiertags_daten(self, feiertage_daten, heute):
        """Verarbeitet die erhaltenen Feiertags-Daten.

        Warum Ostersonntag-Ergaenzung? Die OpenHolidaysAPI liefert
        Ostermontag, aber nicht immer Ostersonntag. Da Ostersonntag ein
        wichtiger Referenztag ist (beginnt das Osterfest), wird er
        automatisch ergänzt — per Gauss-Formel je Jahr im Abruf-Fenster,
        sprachunabhaengig (kein Namens-Match mehr).
        """
        try:
            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

            # Ostersonntag sprachunabhaengig per Gauss ergaenzen. Warum nicht
            # mehr Namens-Match? Die API liefert Ostermontag unter beliebigen
            # Sprach-Labels — der alte Match ("ostermontag"/"easter monday")
            # brach bei anderen Sprachen (FRD-Bug). Gauss berechnet das
            # Osterdatum pro Kalenderjahr der Jahre, die das Abruf-Fenster
            # [heute-30d, heute+365d] beruehrt (Jahr-Set, keine Fenster-Klammer:
            # ein Osterdatum kann vor dem Fensterstart liegen — unschaedlich,
            # da datumsbasiert dedupliziert und nur Attribut-Liste).
            # Nur bei vorhandenen Daten: eine leere API-Antwort bleibt leer
            # (Bestandsverhalten, "keine Daten" ist keine Teil-Lieferung).
            if feiertage_liste:
                fenster_jahre = {
                    heute.year,
                    (heute - timedelta(days=30)).year,
                    (heute + timedelta(days=365)).year,
                }
                for jahr in fenster_jahre:
                    ostersonntag_datum = berechne_ostersonntag(jahr)
                    # Doppelten Eintrag vermeiden (API koennte ihn bereits liefern)
                    if not any(
                        f["start_datum"] == ostersonntag_datum
                        for f in feiertage_liste
                    ):
                        feiertage_liste.append({
                            "name": "Ostersonntag",
                            "start_datum": ostersonntag_datum,
                            "end_datum": ostersonntag_datum,
                        })
            self._feiertags_info["feiertage_liste"] = feiertage_liste
        # pylint: disable=broad-exception-caught
        except Exception as e:
            _LOGGER.error("Fehler beim Verarbeiten der Daten: %s", e)
        # pylint: enable=broad-exception-caught
            return

        aktueller_feiertag = next(
            (
                feiertag
                for feiertag in feiertage_liste
                if feiertag["start_datum"] <= heute <= feiertag["end_datum"]
            ),
            None,
        )

        if aktueller_feiertag:
            self._feiertags_info.update({
                "heute_feiertag": True,
                "naechster_feiertag_name": aktueller_feiertag["name"],
                "naechster_feiertag_datum": aktueller_feiertag["start_datum"].strftime(
                    "%d.%m.%Y"
                ),
            })
        else:
            self._feiertags_info["heute_feiertag"] = False
            zukunft_feiertage = [
                feiertag for feiertag in feiertage_liste if feiertag["start_datum"] > heute
            ]
            if zukunft_feiertage:
                naechster_feiertag = min(
                    zukunft_feiertage,
                    key=lambda f: f["start_datum"]
                )
                self._feiertags_info.update({
                    "naechster_feiertag_name": naechster_feiertag["name"],
                    "naechster_feiertag_datum": naechster_feiertag["start_datum"].strftime(
                        "%d.%m.%Y"
                    ),
                })

class FeiertagMorgenSensor(SensorEntity):
    """Sensor für Feiertag morgen.

    Warum Referenzsensor? Gleiche Strategie wie bei SchulferienMorgenSensor:
    Der Hauptsensor (FeiertagSensor) hat die Daten bereits von der API.
    Statt die API zweimal aufzurufen, liest dieser Sensor die bereits
    geladenen Daten des Hauptsensors aus.

    Warum `feiertage_liste or []`? Verhindert TypeError wenn
    feiertage_liste None ist (Bug 1 Fix).
    """

    def __init__(self, referenzsensor: FeiertagSensor):
        """Erstellt den Morgen-Sensor basierend auf dem Hauptsensor.

        Args:
            referenzsensor: Der Hauptsensor (FeiertagSensor) dessen Daten verwendet werden.
        """
        self.entity_description = FEIERTAG_MORGEN_SENSOR
        self._referenzsensor = referenzsensor
        # Name vom Referenzsensor ableiten: "Feiertag - Bayern" → "Feiertag Morgen - Bayern"
        base_name = referenzsensor._name
        if " - " in base_name:
            self._attr_name = f"Feiertag Morgen{base_name[base_name.index(' - '):]}"
        else:
            self._attr_name = f"{base_name} Morgen"
        # Unique ID und Entity ID vom Referenzsensor ableiten (_morgen Suffix)
        base_unique_id = referenzsensor.unique_id
        self._attr_unique_id = f"{base_unique_id}_morgen"
        # Suggested Object ID aus der Unique ID ableiten (kleingeschrieben):
        # "feiertag_DE_RP" -> "feiertag_de_rp_morgen" ->
        # sensor.feiertag_de_rp_morgen. Warum nicht von der entity_id des
        # Referenzsensors? Vor dem Add an HA ist entity_id noch nicht gesetzt.
        self._suggested_object_id = f"{base_unique_id.lower()}_morgen"

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def suggested_object_id(self):
        """Gibt die vorgeschlagene Entity-ID ohne Domain-Praefix zurück.

        Siehe FeiertagSensor.suggested_object_id: HA weist entity_id selbst
        zu, wir schlagen nur die gewuenschte ID vor.
        """
        return self._suggested_object_id

    @property
    def name(self):
        return self._attr_name

    @property
    def native_value(self):
        """Gibt den aktuellen Zustand des Sensors zurück.

        Warum morgen = heute + 1 Tag? Dieser Sensor soll anzeigen ob
        MORGEN ein Feiertag ist.
        """
        morgen = dt_util.now().date() + timedelta(days=1)
        # pylint: disable=protected-access
        # Oder-Operator verhindert TypeError bei None (Bug 1 Fix)
        for feiertag in self._referenzsensor._feiertags_info.get("feiertage_liste") or []:
        # pylint: enable=protected-access
            if feiertag["start_datum"] == morgen:
                return "feiertag"
        return "kein_feiertag"

    # pylint: disable=missing-function-docstring
    async def async_update(self):
        pass
