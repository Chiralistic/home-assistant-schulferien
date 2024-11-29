from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_STATE
from .const import DOMAIN

class SchulferienConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Schulferien integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration."""
        errors = {}

        # Prüfen, ob der Benutzer Eingaben gemacht hat
        if user_input is not None:
            # Validierung der Eingaben
            if not user_input.get(CONF_NAME):
                errors["base"] = "name_required"
            elif not user_input.get(CONF_STATE):
                errors["base"] = "state_required"
            else:
                # Konfiguration speichern
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        # Zeige das Formular mit Fehlern oder Standardwerten
        return self.async_show_form(
            step_id="user",
            data_schema=self._get_form_schema(),
            errors=errors,
        )

    def _get_form_schema(self):
        """Return the input form schema."""
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required(CONF_NAME, default="Schulferien"): str,
                vol.Required(CONF_STATE, default="DE-NI"): str,
            }
        )
