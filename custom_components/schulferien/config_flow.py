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

    def _get_hass_language(self, hass: HomeAssistant) -> str:
        """Holt den aktuellen Sprachcode aus der Home Assistant-Konfiguration und formatiert ihn."""
        language = hass.config.language[:2].upper()  # Ersten zwei Buchstaben großschreiben, z. B. "DE".
        _LOGGER.debug("Ermittelte Sprache aus Home Assistant: %s", language)
        return language

    async def _fetch_supported_countries(self) -> dict:
        """Holt die Liste der unterstützten Länder von der API."""
        url = f"https://openholidaysapi.org/Countries?languageIsoCode={self.language_iso_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # Debugging: API-Antwort prüfen
                    _LOGGER.debug("API-Antwort für Länder: %s", await response.text())
                    try:
                        countries_data = await response.json()
                        return {
                            country["isoCode"]: next(
                                (name_entry["text"] for name_entry in country["name"] if name_entry["language"] == self.language_iso_code),
                                country["isoCode"]  # Fallback, falls die Sprache nicht gefunden wird
                            )
                            for country in countries_data if "name" in country
                        }
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
                        return {
                            subdivision["code"]: next(
                                (name_entry["text"] for name_entry in subdivision["name"] if name_entry["language"] == self.language_iso_code),
                                subdivision["code"]  # Fallback, falls die Sprache nicht gefunden wird
                            )
                            for subdivision in subdivisions_data if "name" in subdivision
                        }
                    except (KeyError, ValueError, TypeError) as e:
                        _LOGGER.error("Fehler beim Verarbeiten der API-Antwort für Regionen: %s", e)
                else:
                    _LOGGER.error("Fehler beim Abrufen der Regionen: HTTP %s", response.status)
        return {}

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
            _LOGGER.error("Keine Regionen für Land %s verfügbar.", self.selected_country)
            return self.async_abort(reason="no_regions_available")

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

    async def async_step_finish(self, user_input=None):
        """Prüft die Konfiguration und erstellt den Eintrag."""
        # Sicherstellen, dass Land und Region gesetzt sind
        if not hasattr(self, "selected_country") or not hasattr(self, "selected_region"):
            return self.async_abort(reason="incomplete_configuration")

        # Daten für den Eintrag vorbereiten
        config_data = {
            "country": self.selected_country,
            "region": self.selected_region,
        }

        try:
            return self.async_create_entry(
                title=f"Schulferien - {self.selected_country} ({self.selected_region})",
                data=config_data,
            )
        except (vol.Invalid, KeyError) as e:
            _LOGGER.error("Fehler beim Erstellen des Eintrags: %s", e)
            return self.async_abort(reason="creation_failed")
