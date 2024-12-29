"""Konstanten für die Schulferien- und Feiertags-Integration."""

DOMAIN = "schulferien"
API_URL_FERIEN = "https://openholidaysapi.org/SchoolHolidays"
API_FALLBACK_FERIEN = "https://openholidaysapi.org/Holidays/SchoolHolidays"
API_URL_FEIERTAGE = "https://openholidaysapi.org/PublicHolidays"
API_FALLBACK_FEIERTAGE = "https://openholidaysapi.org/Holidays/PublicHolidays"

# Länder mit ausgeschriebenen Namen und Codes
COUNTRIES = {
    "DE": "Deutschland",
}

# Regionen mit ausgeschriebenen Namen und Codes für Deutschland
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
    }
}
