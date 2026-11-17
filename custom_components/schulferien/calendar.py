"""Kalender-Entitäten für Schulferien und Feiertage.

Warum ein Kalender? Die Sensoren zeigen nur den aktuellen bzw. nächsten
Ferien-/Feiertagszeitraum als Attribut. Die Kalender-Karte (und jede andere
Kalender-Ansicht in HA) braucht aber eine calendar.*-Entity mit allen
Terminen im Zeitraum.

Warum keine eigenen API-Abrufe? Die Sensoren halten die komplette, bereits
geparste Liste (ferien_liste / feiertage_liste, Fenster heute-30d bis
heute+365d) inkl. Brückentagen. Der Kalender liest diese Liste nur aus —
der 3-Regel-Guard der Sensoren bleibt die einzige Stelle, die die API
anfragt.

Warum werden die Sensoren lazy über hass.data aufgelöst? async_forward_entry_setups
lädt die Plattformen parallel; zum Setup-Zeitpunkt des Kalenders ist nicht
garantiert, dass sensor.py seine Instanzen schon registriert hat. Beim
Abfragen der Termine sind sie es.
"""

import logging
from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from .api_utils import compute_region_slug
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup der Kalender für Schulferien und Feiertage."""
    land = config_entry.data.get("land")
    region = config_entry.data.get("region")
    land_name = config_entry.data.get("land_name")
    region_name = config_entry.data.get("region_name")
    region_slug = compute_region_slug(land, region)

    async_add_entities([
        FerienKalender(
            hass,
            config_entry.entry_id,
            sensor_key="schulferien",
            listen_key="ferien_liste",
            info_attr="_ferien_info",
            name=f"Schulferien - {land_name} ({region_name})",
            unique_id=f"kalender_schulferien_{land.upper()}_{region_slug}",
            object_id=f"schulferien_{land.lower()}_{region_slug.lower()}",
            location=f"{land_name}, {region_name}",
        ),
        FerienKalender(
            hass,
            config_entry.entry_id,
            sensor_key="feiertag",
            listen_key="feiertage_liste",
            info_attr="_feiertags_info",
            name=f"Feiertage - {land_name} ({region_name})",
            unique_id=f"kalender_feiertage_{land.upper()}_{region_slug}",
            object_id=f"feiertage_{land.lower()}_{region_slug.lower()}",
            location=f"{land_name}, {region_name}",
        ),
    ])


# Nur lesend: create/update/delete_event bleiben bewusst unimplementiert. HA bietet
# diese Aktionen nur an, wenn supported_features sie meldet (hier: keine).
class FerienKalender(CalendarEntity):  # pylint: disable=abstract-method
    """Kalender, der die Liste eines Schulferien-/Feiertag-Sensors anzeigt.

    Ganztägige Termine: HA erwartet bei date-Events ein exklusives Ende,
    die API liefert ein inklusives endDate — daher end_datum + 1 Tag.

    Polling (Default von CalendarEntity, 60 s) bleibt aktiv: es kostet nur
    einen Listen-Durchlauf im Speicher und hält `event` (aktueller/nächster
    Termin) auch nach einem wöchentlichen Daten-Refresh der Sensoren aktuell.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, hass, entry_id, *, sensor_key, listen_key, info_attr,
                 name, unique_id, object_id, location):
        """Initialisiert den Kalender."""
        self.hass = hass
        self._entry_id = entry_id
        self._sensor_key = sensor_key
        self._listen_key = listen_key
        self._info_attr = info_attr
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._suggested_object_id = object_id
        self._location = location
        self._attr_icon = "mdi:calendar-star" if sensor_key == "feiertag" else "mdi:school"

    @property
    def suggested_object_id(self):
        """Vorgeschlagene Entity-ID ohne Domain-Präfix (siehe SchulferienSensor)."""
        return self._suggested_object_id

    def _eintraege(self):
        """Liefert die Einträge des zugehörigen Sensors (leer, solange keiner da ist)."""
        sensoren = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        sensor = sensoren.get(self._sensor_key)
        if sensor is None:
            return []
        info = getattr(sensor, self._info_attr, None) or {}
        return info.get(self._listen_key) or []

    def _events(self):
        """Wandelt die Sensor-Einträge in sortierte, ganztägige CalendarEvents um."""
        events = []
        for eintrag in self._eintraege():
            start = eintrag.get("start_datum")
            ende = eintrag.get("end_datum")
            if not isinstance(start, date) or not isinstance(ende, date):
                continue
            events.append(CalendarEvent(
                start=start,
                end=ende + timedelta(days=1),
                summary=eintrag.get("name") or "Unbekannt",
                location=self._location,
            ))
        events.sort(key=lambda e: (e.start, e.summary))
        return events

    @property
    def event(self):
        """Aktueller oder nächster Termin (bestimmt den Zustand on/off)."""
        heute = dt_util.now().date()
        return next((e for e in self._events() if e.end > heute), None)

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime):
        """Termine, die den angefragten Zeitraum überschneiden."""
        von = dt_util.as_local(start_date).date()
        ende_lokal = dt_util.as_local(end_date)
        # Exklusives Ende: endet die Abfrage um 00:00, gehört dieser Tag nicht
        # mehr dazu; endet sie mitten am Tag, schon.
        bis = ende_lokal.date()
        if ende_lokal.time() != datetime.min.time():
            bis += timedelta(days=1)
        return [e for e in self._events() if e.start < bis and e.end > von]
