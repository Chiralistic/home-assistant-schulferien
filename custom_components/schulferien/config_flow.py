import logging
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, REGION_TO_API, COUNTRY_TO_API

_LOGGER = logging.getLogger(__name__)

class SchulferienConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Schulferien integration."""
    VERSION = 1

    def __init__(self):
        self.selected_country = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow."""
        errors = {}

        if user_input is not None:
            self.selected_country = user_input["country"]
            return await self.async_step_region()

        # Display the country selection form
        countries = {v: k for k, v in COUNTRY_TO_API.items()}  # Reverse map for display
        default_country = "Germany"  # Default to Germany

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("country", default=default_country): vol.In(countries),
                }
            ),
            errors=errors,
        )

    async def async_step_region(self, user_input=None):
        """Handle the region selection step based on the selected country."""
        errors = {}

        if user_input is not None:
            region = user_input["region"]
            country_code = COUNTRY_TO_API[self.selected_country]
            state_code = REGION_TO_API[country_code].get(region)

            if not state_code:
                errors["base"] = "unsupported_region"
            else:
                return self.async_create_entry(
                    title=f"Schulferien ({region})",
                    data={
                        "country_code": country_code,
                        "state": state_code,
                    },
                )

        # Display the region selection form
        if not self.selected_country:
            return self.async_abort(reason="unknown_error")

        country_code = COUNTRY_TO_API[self.selected_country]
        regions = REGION_TO_API[country_code]
        default_region = list(regions.keys())[0]

        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(
                {
                    vol.Required("region", default=default_region): vol.In(regions),
                }
            ),
            errors=errors,
        )
