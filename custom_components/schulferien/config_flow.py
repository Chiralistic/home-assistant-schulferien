import logging
from homeassistant import config_entries
from homeassistant.const import CONF_COUNTRY, CONF_REGION
from .const import COUNTRY_TO_API

_LOGGER = logging.getLogger(__name__)

class SchulferienConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Schulferien."""

    VERSION = 1

    def __init__(self):
        self._country_code = None
        self._state_code = None

    async def async_step_user(self, user_input=None):
        """Handle the user step."""
        if user_input is not None:
            country_name = user_input[CONF_COUNTRY]
            country_data = COUNTRY_TO_API.get(country_name)
            if country_data:
                self._country_code = country_data["code"]
                self._state_code = user_input[CONF_REGION]
                return self.async_create_entry(
                    title=f"{country_name} - {self._state_code}",
                    data={"country_code": self._country_code, "state": self._state_code},
                )

        # Prepare country options for the user
        countries = {v["translations"]["en"]: k for k, v in COUNTRY_TO_API.items()}

        return self.async_show_form(
            step_id="user", data_schema=self._build_schema(countries)
        )

    def _build_schema(self, countries):
        """Build the data schema for the form."""
        return vol.Schema(
            {
                vol.Required(CONF_COUNTRY): vol.In(countries),
                vol.Required(CONF_REGION): str,
            }
        )
