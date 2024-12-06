# home-assistant-schulferien

Home Assistant-Integration, um Schulferien mithilfe der OpenHolidays-API als Entität für Automationen verfügbar zu machen.

Noch in der Entwicklung, daher Nutzung auf eigene Gefahr.

## Installation

**Manuell**

1. Kopiere den Ordner schulferien in deinen custom_components-Ordner im Hauptverzeichnis deiner Home Assistant-Konfiguration.

2. Erstelle einen Sensor in deiner configuration.yaml:

```yaml
sensor:
  - platform: schulferien
    name: "Schulferien Deutschland Niedersachsen"
    country_code: "DE"
    region: "DE-NI"
```

## Konfiguration

Um das Bundesland der Ferien zu ändern, kannst du die folgenden Ländercodes verwenden:
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

Da diese Integration die OpenHolidaysAPI verwendet, funktionieren wahrscheinlich auch andere Länder und Regionen, jedoch wurde dies nicht getestet.

If you want to monitor multiple states you have to setup multiple sensors. You can add additional days which should count as Holidays

```yaml
sensor:
  - platform: schulferien
    name: "Schulferien Deutschland Niedersachsen"
    country_code: "DE"
    region: "DE-NI"
    bridge_days:
      - "10.05.2024"
      - "04.10.2024"
      - "01.11.2024"
```


Erstelle eine einfache Entitätskarte in deinem Dashboard mit dem folgenden Code:
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
  - type: attribute
    entity: sensor.schulferien
    attribute: Land
    name: Land
  - type: attribute
    entity: sensor.schulferien
    attribute: Region
    name: Region
```

Hier ist eine kurze Karte für das Dashboard, die die Funktion der Brückentage erklärt und die aktuell definierten Brückentage als Attribut auflistet:
```yaml
type: vertical-stack
cards:
  - type: markdown
    content: >
      **Brückentage** sind zusätzliche Tage, die als Ferientage gezählt werden, obwohl sie nicht in der API enthalten sind.
      Diese können in der `configuration.yaml` hinzugefügt werden. Nutze dafür das folgende Format:

      ```yaml
      sensor:
        - platform: schulferien
          name: "Schulferien Deutschland Niedersachsen"
          country_code: "DE"
          region: "DE-NI"
          bridge_days:
            - "10.05.2024"
            - "04.10.2024"
            - "01.11.2024"
      ```

      Jede Zeile in der Liste `bridge_days` muss ein Datum im Format `TT.MM.JJJJ` enthalten.
  - type: markdown
    title: Aktuell eingestellte Brückentage
    content: >
      {% if state_attr('sensor.schulferien', 'Brückentage') %}
      **Brückentage:**
      {% for tag in state_attr('sensor.schulferien', 'Brückentage') %}
      - {{ tag }}
      {% endfor %}
      {% else %}
      Keine Brückentage definiert.
      {% endif %}
```

**English:**


Home Assistant Integration to make the vacations an entity for automations using the OpenHolidays-API.

still very much work in progress so use at your own risk.

## Installation

**Manual**

1. Copy the `schulferien` folder into your `custom_components` folder that is located under the root of your `home assistant config`.

2. Create a sensor in your `configuration.yaml`

```yaml
sensor:
  - platform: schulferien
    name: "Schulferien Deutschland Niedersachsen"
    country_code: "DE"
    region: "DE-NI"
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

This the integration uses the OpenHolidaysAPI other countries and states will probably work but I did't test it.

If you want to monitor multiple states you have to setup multiple sensors. You can add additional days which should count as Holidays

```yaml
sensor:
  - platform: schulferien
    name: "Schulferien Deutschland Niedersachsen"
    country_code: "DE"
    region: "DE-NI"
    bridge_days:
      - "10.05.2024"
      - "04.10.2024"
      - "01.11.2024"
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
  - type: attribute
    entity: sensor.schulferien
    attribute: Land
    name: Land
  - type: attribute
    entity: sensor.schulferien
    attribute: Region
    name: Region
```
Hier ist eine kurze Karte für das Dashboard, die die Funktion der Brückentage erklärt und die aktuell definierten Brückentage als Attribut auflistet:
```yaml
type: vertical-stack
cards:
  - type: markdown
    content: >
      **Bridge Days** are additional days that count as holidays, even though they are not included in the API.
      You can add these in the `configuration.yaml`. Use the following format:

      ```yaml
      sensor:
        - platform: schulferien
          name: "School Holidays Germany Lower Saxony"
          country_code: "DE"
          region: "DE-NI"
          bridge_days:
            - "10.05.2024"
            - "04.10.2024"
            - "01.11.2024"
      ```

      Each line in the `bridge_days` list must include a date in the format `DD.MM.YYYY`.
  - type: markdown
    title: Selected Bridge Days
    content: >
      {% if state_attr('sensor.schulferien', 'Brückentage') %}
      **Bridge Days:**
      {% for tag in state_attr('sensor.schulferien', 'Brückentage') %}
      - {{ tag }}
      {% endfor %}
      {% else %}
      No Bridge Day defined.
      {% endif %}
```

