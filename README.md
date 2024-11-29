# home-assistant-schulferien

Home Assistant Integration to make the German vacations an entity for automations using the OpenHolidays-API.

still very much work in progress so use at your own risk.

## Installation

**Manual**

1. Copy the `schulferien` folder into your `custom_components` folder that is located under the root of your `home assistant config`.

2. Create a sensor in your `configuration.yaml`

```yaml
sensor:
  - platform: schulferien
    name: Schulferien Niedersachsen
    state: DE-NI
    hour: 4  # Uhrzeit der Abfrage (Standard: 3)
    minute: 30  # Minute der Abfrage (Standard: 0)
    cache_duration: 24  # Cache-Gültigkeitsdauer in Stunden (Standard: 24 Stunden)
    max_retries: 3  # Maximale Anzahl an Wiederholungen bei API-Fehlern (Standard: 3)

```

To reduce the load on the API you can change the time when the daily API call will be made.

## Configuration

To change the state you can use the following state codes:
Land    | Code
--------|---------
 Baden-Württemberg      |	DE-BW
 Bayern                 |	DE-BY
 Berlin                 |	DE-BE
 Brandenburg            |	DE-BB
 Bremen                 |	DE-HB
 Hamburg                |	DE-HH
 Hessen                 |	DE-HE
 Mecklenburg-Vorpommern |	DE-MV
 Niedersachsen          |	DE-NI
  Nordrhein-Westfalen   |	DE-NW
 Rheinland-Pfalz        |	DE-RP
 Saarland               |	DE-SL
 Sachsen                |	DE-SN
 Sachsen-Anhalt         |	DE-ST
 Schleswig-Holstein     |	DE-SH
 Thüringen              |	DE-TH

This the integration uses the OpenHolidaysAPI other countries and states will probably work but I did't test it.

If you want to monitor multiple states you have to setup multiple sensors. Some examples:

```yaml
sensor:
  - platform: schulferien
    name: Schulferien Niedersachsen
    country_code: DE  # Ländercode (z. B. DE für Deutschland)
    state: DE-NI
    hour: 43  # Uhrzeit der Abfrage (Standard: 3)
    minute: 30  # Minute der Abfrage (Standard: 0)
    cache_duration: 24  # Cache-Gültigkeitsdauer in Stunden (Standard: 24 Stunden)
    max_retries: 3  # Maximale Anzahl an Wiederholungen bei API-Fehlern (Standard: 3)
sensor:
  - platform: schulferien
    name: Schulferien Niedersachsen
    country_code: DE  # Ländercode (z. B. DE für Deutschland)
    state: DE-HH
    hour: 4  # Uhrzeit der Abfrage (Standard: 3)
    minute: 30  # Minute der Abfrage (Standard: 0)
    cache_duration: 24  # Cache-Gültigkeitsdauer in Stunden (Standard: 24 Stunden)
    max_retries: 3  # Maximale Anzahl an Wiederholungen bei API-Fehlern (Standard: 3)
sensor:
  - platform: schulferien
    name: Schulferien Wien
    country_code: AT  # Österreich
    state: AT-9  # Bundeslandcode für Wien
    hour: 4  # Abfragezeit auf 4 Uhr setzen
    minute: 0
    cache_duration: 48  # Cache bleibt 48 Stunden gültig
    max_retries: 5  # Maximal 5 Wiederholungsversuche
sensor:
  - platform: schulferien
    name: Schulferien Zürich
    country_code: CH  # Schweiz
    state: CH-ZH  # Kanton Zürich
    hour: 2  # Abfragezeit auf 2 Uhr setzen
    minute: 30
    cache_duration: 24
    max_retries: 3

```


You can create a simple Entity Card on your Dashboard with the following code
```yaml
type: entities
title: Schulferien
entities:
  - entity: sensor.schulferien_niedersachsen
    name: Aktueller Status
  - type: attribute
    entity: sensor.schulferien_niedersachsen
    attribute: Nächste Ferien
    name: Name der Ferien
  - type: attribute
    entity: sensor.schulferien_niedersachsen
    attribute: Beginn
    name: Beginn der Ferien
  - type: attribute
    entity: sensor.schulferien_niedersachsen
    attribute: Ende
    name: Ende der Ferien
```