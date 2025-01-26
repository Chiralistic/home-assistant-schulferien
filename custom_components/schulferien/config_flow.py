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
                    countries_data = await response.json()
                    return {
                        country["isoCode"]: country["names"].get(self.language_iso_code, country["isoCode"])
                        for country in countries_data
                        if self.language_iso_code in country["names"]
                    }
                _LOGGER.error("Fehler beim Abrufen der Länder: %s", response.status)
                return {}

    async def _fetch_supported_regions(self, country_code: str) -> dict:
        """Holt die Liste der Regionen basierend auf dem Land von der API."""
        url = f"https://openholidaysapi.org/Regions?countryIsoCode={country_code}&languageIsoCode={self.language_iso_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    regions_data = await response.json()
                    return {
                        region["regionCode"]: region["names"].get(self.language_iso_code, region["regionCode"])
                        for region in regions_data
                        if self.language_iso_code in region["names"]
                    }
                _LOGGER.error("Fehler beim Abrufen der Regionen: %s", response.status)
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
            # Weiter zum nächsten Schritt (Regionen-Auswahl)
            return await self.async_step_region({"country": user_input["country"]})

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

        # Prüfen, ob das Land gesetzt wurde
        country_code = user_input.get("country") if user_input else None
        if not country_code:
            return self.async_abort(reason="missing_country")

        # Regionen abrufen
        regions = await self._fetch_supported_regions(country_code)
        if not regions:
            return self.async_abort(reason="no_regions_available")

        if user_input is not None and "region" in user_input:
            # Fertigstellung
            return await self.async_step_finish(
                {"country": country_code, "region": user_input["region"]}
            )

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
        if user_input is None:
            return self.async_abort(reason="missing_input")

        # Validierung der Eingabedaten
        if not user_input.get("country") or not user_input.get("region"):
            return self.async_abort(reason="incomplete_configuration")

        try:
            return self.async_create_entry(
                title="Schulferien-Integration",
                data=user_input,
            )
        except (vol.Invalid, KeyError) as e:
            _LOGGER.error("Fehler beim Erstellen des Eintrags: %s", e)
            return self.async_abort(reason="creation_failed")
