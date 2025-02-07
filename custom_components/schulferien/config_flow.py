"""Konfigurations-Flow für die Schulferien-Integration."""

from __future__ import annotations

import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SchulferienFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die Schulferien-Integration."""

    def __init__(self):
        """Initialisierung."""
        self.language_iso_code = "DE"  # Fallback-Sprache auf "DE" setzen.
        self.supported_countries = {}
        self.supported_regions = {}

    def _get_hass_language(self, hass: HomeAssistant) -> str:
        """Holt den aktuellen Sprachcode aus der Home Assistant-Konfiguration und formatiert ihn."""
        language = hass.config.language[:2].upper()  # Ersten zwei Buchstaben groß, z.B. "DE"
        _LOGGER.debug("Ermittelte Sprache aus Home Assistant: %s", language)
        return language

    async def _fetch_supported_countries(self) -> dict:
        """Holt die Liste der unterstützten Länder von der API."""
        url = f"https://openholidaysapi.org/Countries?languageIsoCode={self.language_iso_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        countries_data = await response.json()
                        self.supported_countries = {
                            country["isoCode"]: next(
                                (name_entry["text"] for name_entry in country["name"]
                                 if name_entry["language"] == self.language_iso_code),
                                country["isoCode"]  # Fallback
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
        """Holt die Liste der Regionen basierend auf dem Land von der API."""
        url = f"https://openholidaysapi.org/Subdivisions?countryIsoCode={country_code}&languageIsoCode={self.language_iso_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # Debugging: API-Antwort prüfen
                    _LOGGER.debug("API-Antwort für Regionen: %s", await response.text())
                    try:
                        subdivisions_data = await response.json()
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
                        return {}  # Fehlerbehandlung, falls die Antwort nicht wie erwartet ist
                else:
                    _LOGGER.error("Fehler beim Abrufen der Regionen: HTTP %s", response.status)
                    return {}  # Rückgabe einer leeren Liste, wenn der HTTP-Status nicht 200 ist

    async def async_step_user(self, user_input=None):
        """Erster Schritt: Auswahl des Landes."""
        errors = {}

        # Sprache von Home Assistant holen
        self.language_iso_code = self._get_hass_language(self.hass)

        # Länder abrufen
        countries = await self._fetch_supported_countries()
        if not countries:
            return self.async_abort(reason="no_countries_available")

        if user_input is not None:
            # Benutzer hat ein Land ausgewählt
            self.selected_country = user_input["country"]  # Speichern des Landes
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
        """Zweiter Schritt: Auswahl der Region basierend auf dem Land."""
        errors = {}

        # Sicherstellen, dass ein Land ausgewählt wurde
        if not hasattr(self, "selected_country") or not self.selected_country:
            return self.async_abort(reason="missing_country")

        # Regionen abrufen
        regions = await self._fetch_supported_regions(self.selected_country)

        if not regions:
            # Wenn keine Regionen verfügbar sind, setze eine Standardregion (DE-NS)
            _LOGGER.warning(
                "Keine Regionen für Land %s verfügbar, setze Standardregion DE-NS.", self.selected_country
            )
            regions = {"DE-NS": "Keine Regionen"}

        if user_input is not None:
            # Benutzer hat eine Region ausgewählt
            self.selected_region = user_input["region"]  # Speichern der Region
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
        """Prüft die Konfiguration und erstellt den Eintrag."""
        # Sicherstellen, dass Land und Region gesetzt sind
        if not hasattr(self, "selected_country") or not hasattr(self, "selected_region"):
            return self.async_abort(reason="incomplete_configuration")

        # Daten für den Eintrag vorbereiten
        config_data = {
            "land": self.selected_country,
            "region": self.selected_region,
            "land_name": self.supported_countries.get(
                self.selected_country, self.selected_country
            ),
            "region_name": self.supported_regions.get(
                self.selected_country, {}
            ).get(self.selected_region, self.selected_region),
        }

        _LOGGER.debug("Erstelle Eintrag mit Konfigurationsdaten: %s", config_data)

        try:
            return self.async_create_entry(
                title=f"Schulferien - {config_data['land_name']} ({config_data['region_name']})",
                data=config_data,
            )
        except (vol.Invalid, KeyError) as e:
            _LOGGER.error("Fehler beim Erstellen des Eintrags: %s", e)
            return self.async_abort(reason="creation_failed")
