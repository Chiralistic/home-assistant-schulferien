"""Konfigurations-Flow für die Schulferien-Integration.

2-Schritt-Flow:
1. Nutzer wählt Land (z.B. Deutschland, Österreich, Schweiz)
2. Nutzer wählt Region (z.B. Bayern, Baden-Württemberg)

Warum 2 Schritte? Die API hat ~200 Länder mit unterschiedlichen Regionen.
Ein einziger Dropdown wäre überladen. Land → Region ist intuitiv und
skaliert gut mit neuen Ländern/Regionen.

Sprachcode: Der Flow verwendet die HA-Sprache (z.B. "de" → "DE")
um Länder- und Regionsnamen lokalisiert anzuzeigen. Die API unterstützt
isoCode-basierte Lokalisierung (DE, AT, CH, etc.).
"""

from __future__ import annotations

import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# pylint: disable=abstract-method
class SchulferienFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die Schulferien-Integration.

    State wird in Instanzvariablen über Schritt-Grenzen hinweg gespeichert:
    - language_iso_code: Sprachcode für API-Anfragen (DE, AT, CH, etc.)
    - supported_countries: {isoCode: lokalerName} — zwischengespeichert
    - supported_regions: {countryCode: {regionCode: lokalerName}}
    - selected_country/region: Vom Nutzer gewählte Werte
    """

    def __init__(self):
        """Initialisierung des Config-Flows."""
        # pylint: disable=invalid-name
        # Sprachcode für API-Anfragen — wird in async_step_user gesetzt
        self.language_iso_code = "DE"
        # Zwischengespeicherte Länder/Regionen von der API
        self.supported_countries = {}
        self.supported_regions = {}
        # Vom Nutzer gewählte Werte (über Schritt-Grenzen hinweg)
        self.selected_country = None
        self.selected_region = None

    def _get_hass_language(self, hass: HomeAssistant) -> str:
        """Holt den Sprachcode aus der Home Assistant-Konfiguration.

        Warum 2-stellig und uppercase? Die OpenHolidaysAPI erwartet
        ISO 639-1 Codes (DE, EN, FR...) in uppercase. HA speichert
        Sprachen oft als "de-DE" oder "de_DE" — wir brauchen nur
        die ersten 2 Zeichen in uppercase.
        """
        language = hass.config.language[:2].upper()
        _LOGGER.debug("Ermittelte Sprache aus Home Assistant: %s", language)
        return language

    async def _fetch_supported_countries(self) -> dict:
        """Holt die Liste der unterstützten Länder von der API.

        Warum separat? Die Länderliste wird nur einmal pro Flow-Instanz
        gebraucht und kann für alle nachfolgenden Schritte wiederverwendet
        werden. Das Ergebnis wird in self.supported_countries gespeichert.

        Returns:
            Dict {isoCode: lokalerName} oder leeres Dict bei Fehler.
        """
        url = f"https://openholidaysapi.org/Countries?languageIsoCode={self.language_iso_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        countries_data = await response.json()
                        # Lokalierte Namen extrahieren — fallback auf isoCode
                        self.supported_countries = {
                            country["isoCode"]: next(
                                (name_entry["text"] for name_entry in country["name"]
                                 if name_entry["language"] == self.language_iso_code),
                                country["isoCode"]
                            )
                            for country in countries_data if "name" in country
                        }
                        return self.supported_countries
                    except (KeyError, ValueError, TypeError) as e:
                        _LOGGER.error("Fehler beim Verarbeiten der API-Antwort für Länder: %s", e)
                else:
                    _LOGGER.error("Fehler beim Abrufen der Länder: HTTP %s", response.status)
        return {}

    async def _fetch_supported_regions(self, country_code: str) -> dict:
        """Holt die Liste der Regionen basierend auf dem Land von der API.

        Warum separat? Jede Land hat unterschiedliche Regionen (Bundesländer, Kantone, etc.).
        Das Ergebnis wird in self.supported_regions[country_code] gespeichert.

        Args:
            country_code: ISO-Ländercode (z.B. "DE", "AT", "CH")

        Returns:
            Dict {regionCode: lokalerName} oder leeres Dict bei Fehler.
        """
        url = (
            f"https://openholidaysapi.org/Subdivisions"
            f"?countryIsoCode={country_code}"
            f"&languageIsoCode={self.language_iso_code}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    _LOGGER.debug("API-Antwort für Regionen: %s", await response.text())
                    try:
                        subdivisions_data = await response.json()
                        # Lokalierte Namen extrahieren — fallback auf region code
                        self.supported_regions[country_code] = {
                            subdivision["code"]: next(
                                (name_entry["text"] for name_entry in subdivision["name"]
                                if name_entry["language"] == self.language_iso_code),
                                subdivision["code"]
                            )
                            for subdivision in subdivisions_data if "name" in subdivision
                        }
                        return self.supported_regions[country_code]
                    except (KeyError, ValueError, TypeError) as e:
                        _LOGGER.error("Fehler beim Verarbeiten der API-Antwort für Regionen: %s", e)
                        return {}
                else:
                    _LOGGER.error("Fehler beim Abrufen der Regionen: HTTP %s", response.status)
                    return {}

    async def async_step_user(self, user_input=None):
        """Erster Schritt: Auswahl des Landes.

        Warum zuerst Land? Die Regionen sind länderspezifisch.
        Erst nach Land-Auswahl können die passenden Regionen geladen werden.

        Der Sprachcode wird hier aus HA konfiguriert, da er für
        die API-Lokalisierung benötigt wird.
        """
        errors = {}

        # Sprachcode aus HA holen — wird für API-Lokalisierung aller folgenden Schritte gebraucht
        self.language_iso_code = self._get_hass_language(self.hass)

        # Länderliste von API laden
        countries = await self._fetch_supported_countries()
        if not countries:
            # API konnte keine Länder liefern → Flow abbrechen
            return self.async_abort(reason="no_countries_available")

        if user_input is not None:
            # Nutzer hat Land gewählt → zum nächsten Schritt wechseln
            self.selected_country = user_input["country"]
            return await self.async_step_region()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("country"): vol.In(countries),
                }
            ),
            errors=errors,
        )

    async def async_step_region(self, user_input=None):
        """Zweiter Schritt: Auswahl der Region basierend auf dem Land.

        Warum Fallback auf "Ganzes Land"? Nicht alle Länder haben
        Regionen in der API (oder die API antwortet nicht). In diesem Fall
        wird das gesamte Land als einzige Option angeboten.
        """
        errors = {}

        # Sicherheitscheck: selected_country muss existieren (Flow-Integrität)
        if not hasattr(self, "selected_country") or not self.selected_country:
            return self.async_abort(reason="missing_country")

        # Regionen für das gewählte Land laden
        regions = await self._fetch_supported_regions(self.selected_country)

        # Fallback: Keine Regionen verfügbar → ganzes Land als Option
        if not regions:
            _LOGGER.warning(
                "Keine Regionen für Land %s verfügbar, "
                "verwende Land-Code als Region.",
                self.selected_country,
            )
            regions = {
                self.selected_country: (
                    f"{self.supported_countries.get(self.selected_country, self.selected_country)}"
                    " (Ganzes Land)"
                )
            }

        if user_input is not None:
            # Nutzer hat Region gewählt → finalen Schritt ausführen
            self.selected_region = user_input["region"]
            return await self.async_step_finish()

        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(
                {
                    vol.Required("region"): vol.In(regions),
                }
            ),
            errors=errors,
        )

    async def async_step_finish(self):
        """Prüft die Konfiguration und erstellt den Eintrag.

        Warum die mehrfachen Checks? ConfigEntries können manuell bearbeitet
        werden (z.B. in configuration.yaml). Ein Eintrag ohne Land/Region
        ist möglich, also muss async_step_finish auch ohne vorherigen Flow
        funktionieren.
        """
        # Validiere dass beide Werte gesetzt sind (manuelle Edit-Resilienz)
        if not hasattr(self, "selected_country") or self.selected_country is None or \
           not hasattr(self, "selected_region") or self.selected_region is None:
            return self.async_abort(reason="incomplete_configuration")

        # Lokalierte Namen auflösen — Fallback auf Codes falls API-Daten fehlen
        land_name = self.supported_countries.get(self.selected_country)
        if land_name is None:
            _LOGGER.warning(
                "Ländername für '%s' nicht gefunden, verwende Code.",
                self.selected_country,
            )
            land_name = self.selected_country

        region_name = self.supported_regions.get(
            self.selected_country, {}
        ).get(self.selected_region)
        if region_name is None:
            _LOGGER.warning(
                "Regionsname für '%s' in Land '%s' nicht gefunden, "
                "verwende Code.",
                self.selected_region,
                self.selected_country,
            )
            region_name = self.selected_region

        config_data = {
            "land": self.selected_country,
            "region": self.selected_region,
            "land_name": land_name,
            "region_name": region_name,
        }

        _LOGGER.debug("Erstelle Eintrag mit Konfigurationsdaten: %s", config_data)

        if not config_data.get("land") or not config_data.get("region"):
            _LOGGER.error("Konfigurationsdaten unvollständig: %s", config_data)
            return self.async_abort(reason="incomplete_configuration")

        try:
            # Eintragstitel für UI: "Schulferien - Deutschland (Bayern)"
            entry_title = f"Schulferien - {config_data['land_name']} ({config_data['region_name']})"
            return self.async_create_entry(
                title=entry_title,
                data=config_data,
            )
        except (vol.Invalid, KeyError) as e:
            _LOGGER.error("Fehler beim Erstellen des Eintrags: %s", e)
            return self.async_abort(reason="creation_failed")
