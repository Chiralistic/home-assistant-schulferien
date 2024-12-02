# home-assistant-schulferien

Home Assistant Integration to make the German vacations an entity for automations using the OpenHolidays-API.

still very much work in progress so use at your own risk.

## Installation

**Manual**

1. Copy the `schulferien` folder into your `custom_components` folder that is located under the root of your `home assistant config`.

2. Add the Integration over the Home Assistant GUI and select your country and region

3. You can create a simple Entity Card on your Dashboard with the following code
```yaml
type: entities
title: Schulferien
entities:
  - entity: sensor.schulferien
    name: Aktueller Status
  - type: attribute
    entity: sensor.schulferien
    attribute: Nächste Ferien
    name: Name der nächsten Ferien
  - type: attribute
    entity: sensor.schulferien
    attribute: Beginn
    name: Beginn der nächsten Ferien
  - type: attribute
    entity: sensor.schulferien
    attribute: Ende
    name: Ende der nächsten Ferien

```
4. Restart HA