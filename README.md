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
```

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

This the integration uses the OpenHolidaysAPI other countries abd states will probably work but I did't test it.

If you want to monitor multiple states you have to setup multiple sensors:

```yaml
sensor:
  - platform: schulferien
    name: Schulferien Niedersachsen
    state: DE-NI
  - platform: schulferien
    name: Schulferien Hamburg
    state: DE-HH
```
