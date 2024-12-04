# /custom_components/schulferien/config_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, UNTERSTÜTZTE_LÄNDER, REGIONEN

@config_entries.HANDLERS.register(DOMAIN)
class SchulferienConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow für die Schulferien-Integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt: Land auswählen."""
        if user_input is not None:
            self.land = user_input["land"]
            return await self.async_step_region()

        schema = vol.Schema(
            {
                vol.Required("land"): vol.In(UNTERSTÜTZTE_LÄNDER),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_region(self, user_input=None):
        """Zweiter Schritt: Region (z. B. Bundesland) auswählen."""
        if user_input is not None:
            return self.async_create_entry(
                title="Schulferien",
                data={
                    "land": self.land,
                    "region": user_input["region"],
                },
            )

        schema = vol.Schema(
            {
                vol.Required("region"): vol.In(REGIONEN[self.land]),
            }
        )
        return self.async_show_form(step_id="region", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Rückgabe der Optionen (falls benötigt)."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Optionen für die Integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Start des Optionen-Workflows."""
        return self.async_show_form(step_id="init")
