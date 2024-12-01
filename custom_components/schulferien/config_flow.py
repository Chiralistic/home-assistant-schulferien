from homeassistant import config_entries
from .const import DOMAIN

# Mapping für Länder und Regionen (Home Assistant zu API)
COUNTRY_TO_API = {
    "Germany": "DE",
    "Austria": "AT",
    "Switzerland": "CH",
    "United States": "US",
    "United Kingdom": "UK",
}


REGION_TO_API = {
    "DE": {
        "Baden-Württemberg": "DE-BW",
        "Bayern": "DE-BY",
        "Berlin": "DE-BE",
        "Brandenburg": "DE-BB",
        "Bremen": "DE-HB",
        "Hamburg": "DE-HH",
        "Hessen": "DE-HE",
        "Mecklenburg-Vorpommern": "DE-MV",
        "Niedersachsen": "DE-NI",
        "Nordrhein-Westfalen": "DE-NW",
        "Rheinland-Pfalz": "DE-RP",
        "Saarland": "DE-SL",
        "Sachsen": "DE-SN",
        "Sachsen-Anhalt": "DE-ST",
        "Schleswig-Holstein": "DE-SH",
        "Thüringen": "DE-TH",
    },
        "AT": {
        "Burgenland": "AT-1",
        "Kärnten": "AT-2",
        "Niederösterreich": "AT-3",
        "Oberösterreich": "AT-4",
        "Salzburg": "AT-5",
        "Steiermark": "AT-6",
        "Tirol": "AT-7",
        "Vorarlberg": "AT-8",
        "Wien": "AT-9",
    },
    "CH": {
        "Zürich": "CH-ZH",
        "Bern": "CH-BE",
        "Luzern": "CH-LU",
        "Uri": "CH-UR",
        "Schwyz": "CH-SZ",
        "Obwalden": "CH-OW",
        "Nidwalden": "CH-NW",
        "Glarus": "CH-GL",
        "Zug": "CH-ZG",
        "Freiburg": "CH-FR",
        "Solothurn": "CH-SO",
        "Basel-Stadt": "CH-BS",
        "Basel-Landschaft": "CH-BL",
        "Schaffhausen": "CH-SH",
        "Appenzell Ausserrhoden": "CH-AR",
        "Appenzell Innerrhoden": "CH-AI",
        "Sankt Gallen": "CH-SG",
        "Graubünden": "CH-GR",
        "Aargau": "CH-AG",
        "Thurgau": "CH-TG",
        "Tessin": "CH-TI",
        "Waadt": "CH-VD",
        "Wallis": "CH-VS",
        "Neuenburg": "CH-NE",
        "Genf": "CH-GE",
        "Jura": "CH-JU",
    },
    "US": {
        "Alabama": "US-AL",
        "Alaska": "US-AK",
        "Arizona": "US-AZ",
        "Arkansas": "US-AR",
        "California": "US-CA",
        "Colorado": "US-CO",
        "Connecticut": "US-CT",
        "Delaware": "US-DE",
        "Florida": "US-FL",
        "Georgia": "US-GA",
        "Hawaii": "US-HI",
        "Idaho": "US-ID",
        "Illinois": "US-IL",
        "Indiana": "US-IN",
        "Iowa": "US-IA",
        "Kansas": "US-KS",
        "Kentucky": "US-KY",
        "Louisiana": "US-LA",
        "Maine": "US-ME",
        "Maryland": "US-MD",
        "Massachusetts": "US-MA",
        "Michigan": "US-MI",
        "Minnesota": "US-MN",
        "Mississippi": "US-MS",
        "Missouri": "US-MO",
        "Montana": "US-MT",
        "Nebraska": "US-NE",
        "Nevada": "US-NV",
        "New Hampshire": "US-NH",
        "New Jersey": "US-NJ",
        "New Mexico": "US-NM",
        "New York": "US-NY",
        "North Carolina": "US-NC",
        "North Dakota": "US-ND",
        "Ohio": "US-OH",
        "Oklahoma": "US-OK",
        "Oregon": "US-OR",
        "Pennsylvania": "US-PA",
        "Rhode Island": "US-RI",
        "South Carolina": "US-SC",
        "South Dakota": "US-SD",
        "Tennessee": "US-TN",
        "Texas": "US-TX",
        "Utah": "US-UT",
        "Vermont": "US-VT",
        "Virginia": "US-VA",
        "Washington": "US-WA",
        "West Virginia": "US-WV",
        "Wisconsin": "US-WI",
        "Wyoming": "US-WY",
    },
    "UK": {
        "England": "UK-ENG",
        "Wales": "UK-WLS",
        "Schottland": "UK-SCT",
        "Nordirland": "UK-NIR",
    },
}

class SchulferienConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Schulferien integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """
        Konfigurations-Schritt: Automatische Verwendung von Home Assistant-Daten.
        """
        # Bestimme Land und Region aus Home Assistant
        country_name = self.hass.config.country
        region_name = self.hass.config.region

        # Übersetze Land und Region für die API
        country_code = COUNTRY_TO_API.get(country_name, "DE")  # Fallback zu DE
        region_code = REGION_TO_API.get(country_code, {}).get(region_name)

        # Fehlerfall: Region nicht gefunden
        if not region_code:
            return self.async_abort(reason="region_not_supported")

        # Eintrag erstellen
        return self.async_create_entry(
            title=f"Schulferien ({region_name})",
            data={
                "country_code": country_code,
                "state": region_code,
            },
        )
