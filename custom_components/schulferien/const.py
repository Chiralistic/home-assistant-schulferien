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

# Tägliche State-Aktualisierung um 00:05. Reiner Recompute ohne
# API-Abruf: native_value ist datumssensitiv und muss beim Datumswechsel neu
# publiziert werden, sonst bleibt ein beendeter Ferien-/Feiertagszeitraum bis zum
# nächsten (wöchentlichen) Abruf als aktiv stehen. 5 Minuten nach Mitternacht
# statt exakt 00:00, damit eine leicht nachlaufende Systemuhr nicht im Vortag
# festhängt. SECOND=0, damit der async_track_time_change-Listener genau einmal
# pro Tag feuert (ohne second matcht er jede Sekunde der Stunde -> 60 Fires).
MIDNIGHT_REFRESH_HOUR = 0
MIDNIGHT_REFRESH_MINUTE = 5
MIDNIGHT_REFRESH_SECOND = 0
