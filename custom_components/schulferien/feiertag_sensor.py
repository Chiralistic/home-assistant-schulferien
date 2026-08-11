"""Modul für die Verwaltung und den Abruf von Feiertagen.

Zwei Sensor-Klassen:
1. FeiertagSensor — Hauptsensor mit API-Abfrage
2. FeiertagMorgenSensor — Spiegel-Sensor für morgen (liest vom Hauptsensor)

Warum Ostersonntag-Workaround? Die OpenHolidaysAPI liefert Ostermontag,
aber nicht immer Ostersonntag. Da Ostersonntag ein wichtiger Referenztag
ist (beginnt das Osterfest), wird er automatisch ergänzt wenn Ostermontag
gefunden wird (Ostersonntag = Ostermontag - 1 Tag).
"""

import logging
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
import aiohttp
from .api_utils import fetch_data, parse_daten, DEFAULT_TIMEOUT, compute_region_slug
from .const import (
    API_URL_FEIERTAGE,
    API_FALLBACK_FEIERTAGE,
    DAILY_UPDATE_HOUR,
    DAILY_UPDATE_MINUTE
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

class FeiertagSensor(SensorEntity):
    """Sensor für Feiertage.

    Hauptverantwortlichkeiten:
    - API-Abfrage der Feiertagsdaten (OpenHolidaysAPI)
    - Berechnung ob heute ein Feiertag ist
    - Angabe des nächsten Feiertags (Name, Datum)
    - Ostersonntag-Workaround: wird automatisch ergänzt wenn Ostermontag gefunden wird

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
        # Alle Feiertagsdaten und Berechnungen
        self._feiertags_info = {
            "heute_feiertag": None,
            "naechster_feiertag_name": None,
            "naechster_feiertag_datum": None,
            "feiertage_liste": [],
            "letztes_update": None,
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
        jetzt = datetime.now()

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

    async def async_will_remove_from_hass(self):
        """Cleanup: Entfernt den taeglichen Timer-Listener.
        Warum wichtig? Ohne Cleanup feuert der Listener weiter,
        nachdem die Entity aus HA entfernt wurde (z.B. bei Multi-Instance-Unload).
        """
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None
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
        """Gibt den aktuellen Zustand des Sensors zurück."""
        return "feiertag" if self._feiertags_info.get("heute_feiertag", False) else "kein_feiertag"

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Statusattribute des Sensors zurück."""
        heute = datetime.now().date()
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
        """
        Aktualisiert die Feiertagsdaten durch Abfrage der API.
        """
        jetzt = datetime.now()
        heute = jetzt.date()
        letztes_update = self._feiertags_info.get("letztes_update")

        # Falls das letzte Update am selben Tag war, wird es übersprungen
        if letztes_update and letztes_update.date() == heute:
            _LOGGER.debug(
                "Update übersprungen. Letztes Update war am: %s",
                letztes_update.date(),
            )
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

            self._feiertags_info["letztes_update"] = jetzt
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
        """Versucht, die Feiertagsdaten von der API abzurufen."""
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

        Warum Ostersonntag-Workaround? Die OpenHolidaysAPI liefert
        Ostermontag, aber nicht immer Ostersonntag. Da Ostersonntag
        ein wichtiger Referenztag ist (beginnt das Osterfest), wird
        er automatisch ergänzt — berechnet als Ostermontag - 1 Tag.

        Warum `list(feiertage_liste)` in der for-Schleife? Wir modifizieren
        die Liste während wir darüber iterieren. `list()` erstellt eine
        flache Kopie für die Iteration, die Originalliste wird modifiziert.
        """
        try:
            feiertage_liste = parse_daten(feiertage_daten, typ="feiertage")

            # Ostersonntag automatisch ergänzen wenn Ostermontag gefunden
            for feiertag in list(feiertage_liste):
                name = feiertag["name"].lower()
                if "ostermontag" in name or "easter monday" in name:
                    ostersonntag_datum = feiertag["start_datum"] - timedelta(days=1)
                    # Doppelten Eintrag vermeiden (API könnte ihn bereits liefern)
                    if not any(
                        f["start_datum"] == ostersonntag_datum
                        for f in feiertage_liste
                    ):
                        feiertage_liste.append({
                            "name": "Ostersonntag",
                            "start_datum": ostersonntag_datum,
                            "end_datum": ostersonntag_datum,
                        })
                    break
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
        morgen = datetime.now().date() + timedelta(days=1)
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
