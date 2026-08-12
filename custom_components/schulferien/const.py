"""Konstanten für die Schulferien- und Feiertags-Integration."""

DOMAIN = "schulferien"

# OpenHolidaysAPI-Endpunkte mit Fallback-URLs
API_URL_FERIEN = "https://openholidaysapi.org/SchoolHolidays"
API_FALLBACK_FERIEN = "https://openholidaysapi.org/Holidays/SchoolHolidays"
API_URL_FEIERTAGE = "https://openholidaysapi.org/PublicHolidays"
API_FALLBACK_FEIERTAGE = "https://openholidaysapi.org/Holidays/PublicHolidays"

# Tägliche Aktualisierung um 03:00 Uhr
DAILY_UPDATE_HOUR = 3
DAILY_UPDATE_MINUTE = 0
