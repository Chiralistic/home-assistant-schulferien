# /custom_components/schulferien/const.py

"""Konstanten für die Schulferien-Integration."""

DOMAIN = "schulferien"
API_URL = "https://openholidaysapi.org/SchoolHolidays"
STANDARD_SPRACHE = "DE"

# Unterstützte Länder
UNTERSTÜTZTE_LÄNDER = {
    "Deutschland": "DE",
    "Österreich": "AT",
    "Schweiz": "CH",
}

# Regionen (Bundesländer/Kantone) der unterstützten Länder
REGIONEN = {
    "DE": [
        "DE-BW",  # Baden-Württemberg
        "DE-BY",  # Bayern
        "DE-BE",  # Berlin
        "DE-BB",  # Brandenburg
        "DE-HB",  # Bremen
        "DE-HH",  # Hamburg
        "DE-HE",  # Hessen
        "DE-MV",  # Mecklenburg-Vorpommern
        "DE-NI",  # Niedersachsen
        "DE-NW",  # Nordrhein-Westfalen
        "DE-RP",  # Rheinland-Pfalz
        "DE-SL",  # Saarland
        "DE-SN",  # Sachsen
        "DE-ST",  # Sachsen-Anhalt
        "DE-SH",  # Schleswig-Holstein
        "DE-TH",  # Thüringen
    ],
    "AT": [
        "AT-1",  # Burgenland
        "AT-2",  # Kärnten
        "AT-3",  # Niederösterreich
        "AT-4",  # Oberösterreich
        "AT-5",  # Salzburg
        "AT-6",  # Steiermark
        "AT-7",  # Tirol
        "AT-8",  # Vorarlberg
        "AT-9",  # Wien
    ],
    "CH": [
        "CH-AG",  # Aargau
        "CH-AI",  # Appenzell Innerrhoden
        "CH-AR",  # Appenzell Ausserrhoden
        "CH-BL",  # Basel-Landschaft
        "CH-BS",  # Basel-Stadt
        "CH-BE",  # Bern
        "CH-FR",  # Freiburg
        "CH-GE",  # Genf
        "CH-GL",  # Glarus
        "CH-GR",  # Graubünden
        "CH-JU",  # Jura
        "CH-LU",  # Luzern
        "CH-NE",  # Neuenburg
        "CH-NW",  # Nidwalden
        "CH-OW",  # Obwalden
        "CH-SG",  # St. Gallen
        "CH-SH",  # Schaffhausen
        "CH-SO",  # Solothurn
        "CH-SZ",  # Schwyz
        "CH-TG",  # Thurgau
        "CH-TI",  # Tessin
        "CH-UR",  # Uri
        "CH-VD",  # Waadt
        "CH-VS",  # Wallis
        "CH-ZG",  # Zug
        "CH-ZH",  # Zürich
    ],
}
