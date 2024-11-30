from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_STATE
from .const import DOMAIN

SUPPORTED_COUNTRIES = {
    "DE": {
        "name": "Deutschland",
        "states": {
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
    },
    "AT": {
        "name": "Österreich",
        "states": {
            "AT-1": "Burgenland",
            "AT-2": "Kärnten",
            "AT-3": "Niederösterreich",
            "AT-4": "Oberösterreich",
            "AT-5": "Salzburg",
            "AT-6": "Steiermark",
            "AT-7": "Tirol",
            "AT-8": "Vorarlberg",
            "AT-9": "Wien",
        },
    },
    "CH": {
        "name": "Schweiz",
        "states": {
            "CH-ZH": "Zürich",
            "CH-BE": "Bern",
            "CH-LU": "Luzern",
            "CH-UR": "Uri",
            "CH-SZ": "Schwyz",
            "CH-OW": "Obwalden",
            "CH-NW": "Nidwalden",
            "CH-GL": "Glarus",
            "CH-ZG": "Zug",
        },
    },
}

class SchulferienConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Schulferien integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration."""
        errors = {}

        if user_input is not None:
            country = user_input.get("country_code")
            state = user_input.get("state")

            # Validiere Eingaben
            if not country:
                errors["base"] = "country_required"
            elif not state:
                errors["base"] = "state_required"
            else:
                # Speichere Konfiguration
                return self.async_create_entry(
                    title=f"Schulferien ({state})", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_form_schema(),
            errors=errors,
        )

    def _get_form_schema(self):
        """Erstelle das Schema für die Eingabeform."""
        import voluptuous as vol

        # Dropdown für Länder
        country_choices = {key: value["name"] for key, value in SUPPORTED_COUNTRIES.items()}
        country_code = self.context.get("country_code", "DE")

        # Dropdown für Staaten basierend auf dem Land
        state_choices = SUPPORTED_COUNTRIES.get(country_code, {}).get("states", {})

        return vol.Schema(
            {
                vol.Required("country_code", default=country_code): vol.In(country_choices),
                vol.Required("state", default="DE-NI"): vol.In(state_choices),
            }
        )
