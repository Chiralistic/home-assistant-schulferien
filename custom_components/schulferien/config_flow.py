from homeassistant import config_entries
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

    def __init__(self):
        """Initialize the config flow."""
        self.selected_country = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration."""
        if user_input is not None:
            # Speichere das ausgewählte Land und gehe zum nächsten Schritt
            self.selected_country = user_input["country_code"]
            return await self.async_step_select_state()

        # Erstelle Dropdown für Länder
        country_choices = {key: value["name"] for key, value in SUPPORTED_COUNTRIES.items()}

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_country_schema(country_choices),
        )

    async def async_step_select_state(self, user_input=None):
        """Handle the state selection based on the selected country."""
        if user_input is not None:
            # Erstelle die Konfiguration basierend auf Land und Staat
            return self.async_create_entry(
                title=f"Schulferien ({user_input['state']})",
                data={
                    "country_code": self.selected_country,
                    "state": user_input["state"],
                },
            )

        # Erstelle Dropdown für Staaten basierend auf dem ausgewählten Land
        state_choices = SUPPORTED_COUNTRIES[self.selected_country]["states"]

        return self.async_show_form(
            step_id="select_state",
            data_schema=self._get_state_schema(state_choices),
        )

    def _get_country_schema(self, country_choices):
        """Erstelle das Schema für die Länderauswahl."""
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required("country_code", default="DE"): vol.In(country_choices),
            }
        )

    def _get_state_schema(self, state_choices):
        """Erstelle das Schema für die Staaten-Auswahl."""
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required("state"): vol.In(state_choices),
            }
        )
