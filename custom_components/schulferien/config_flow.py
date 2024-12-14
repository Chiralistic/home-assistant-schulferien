"""Konfigurations-Flow für die Schulferien-Integration."""

from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.helpers import selector

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

COUNTRIES = {
    "DE": "Deutschland",
}

REGIONS = {
    "DE": {
        "DE-BW": "Baden-Württemberg",
        "DE-BY": "Bayern",
        "DE-BE": "Berlin",
        "DE-BB": "Brandenburg",
        "DE-HB": "Bremen",
        "DE-HH": "Hamburg",
        "DE-HE": "Hessen",
        "DE-MV": "Mecklenburg-Vorpommern",
        "DE-NI": "Niedersachsen",
        "DE-NW": "Nordrhein-Westfalen",
        "DE-RP": "Rheinland-Pfalz",
        "DE-SL": "Saarland",
        "DE-SN": "Sachsen",
        "DE-ST": "Sachsen-Anhalt",
        "DE-SH": "Schleswig-Holstein",
        "DE-TH": "Thüringen",
    },
}

class SchulferienFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Schulferien integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            country = user_input["country"]
            region = user_input["region"]
            name = f"Schulferien {COUNTRIES[country]} {REGIONS[country][region]}"

            return self.async_create_entry(
                title=name,
                data={
                    "country": country,
                    "region": region,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("country", default="DE"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[{"value": k, "label": v} for k, v in COUNTRIES.items()]
                        )
                    ),
                    vol.Required("region", default="DE-NI"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[{"value": k, "label": v} for k, v in REGIONS["DE"].items()]
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict) -> data_entry_flow.FlowResult:
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(user_input)

    def is_matching(self):
        """Prüft, ob die Konfiguration passt."""
        return True  # Beispielimplementierung
