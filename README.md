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
    state: DE-NI
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
    state: DE-NI
sensor:
  - platform: schulferien
    state: DE-HH
```


You can create a simple Entity Card on your Dashboard with the following code
```yaml
type: entities
title: Schulferien
entities:
  - entity: sensor.schulferien
    name: Aktueller Status
  - type: attribute
    entity: sensor.schulferien
    attribute: Nächste Ferien
    name: Name der Ferien
  - type: attribute
    entity: sensor.schulferien
    attribute: Beginn
    name: Beginn der Ferien
  - type: attribute
    entity: sensor.schulferien
    attribute: Ende
    name: Ende der Ferien
```