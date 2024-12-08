# home-assistant-schulferien

Home Assistant-Integration, um Schulferien mithilfe der OpenHolidays-API als Entität für Automationen verfügbar zu machen.

## Installation

### Manuell

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
 Baden-Württemberg      | DE-BW
 Bayern                 | DE-BY
 Berlin                 | DE-BE
 Brandenburg            | DE-BB
 Bremen                 | DE-HB
 Hamburg                | DE-HH
 Hessen                 | DE-HE
 Mecklenburg-Vorpommern | DE-MV
 Niedersachsen          | DE-NI
  Nordrhein-Westfalen   | DE-NW
 Rheinland-Pfalz        | DE-RP
 Saarland               | DE-SL
 Sachsen                | DE-SN
 Sachsen-Anhalt         | DE-ST
 Schleswig-Holstein     | DE-SH
 Thüringen              | DE-TH

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

Erstelle eine einfache Entitätskarte, die alle Attribute anzeigt in deinem Dashboard mit dem folgenden Code. Bei Bedarf kann der Stack verkleinert werden um nur die Informationen anzuzeigen, die gewünscht sind.

```yaml
type: vertical-stack
cards:
  - type: entities
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
      - type: attribute
        entity: sensor.schulferien
        attribute: Brückentage
        name: Brückentage

  - type: entities
    title: Feiertage
    entities:
      - entity: sensor.feiertag
        name: Aktueller Status
      - type: attribute
        entity: sensor.feiertag
        attribute: Nächster Feiertag
        name: Name des Feiertags
      - type: attribute
        entity: sensor.feiertag
        attribute: Datum des nächsten Feiertags
        name: Datum des Feiertags
      - type: attribute
        entity: sensor.feiertag
        attribute: Land
        name: Land
      - type: attribute
        entity: sensor.feiertag
        attribute: Region
        name: Region

  - type: entities
    title: Schulferien/Feiertage kombiniert
    entities:
      - entity: sensor.schulferien_feiertag
        name: Aktueller Status

```

Hier ist eine kleine Karte für das Dashboard, die die Funktion der Brückentage erklärt und die aktuell definierten Brückentage als Attribut auflistet:

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

## English
Home Assistant Integration to make the vacations an entity for automations using the OpenHolidays-API.

still very much work in progress so use at your own risk.

## Installation

### Manual

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
 Baden-Württemberg      | DE-BW
 Bayern                 | DE-BY
 Berlin                 | DE-BE
 Brandenburg            | DE-BB
 Bremen                 | DE-HB
 Hamburg                | DE-HH
 Hessen                 | DE-HE
 Mecklenburg-Vorpommern | DE-MV
 Niedersachsen          | DE-NI
  Nordrhein-Westfalen   | DE-NW
 Rheinland-Pfalz        | DE-RP
 Saarland               | DE-SL
 Sachsen                | DE-SN
 Sachsen-Anhalt         | DE-ST
 Schleswig-Holstein     | DE-SH
 Thüringen              | DE-TH

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

Create a simple entity card that displays all attributes on your dashboard with the following code. If necessary, the stack can be reduced to show only the desired information.

```yaml
type: vertical-stack
cards:
  - type: entities
    title: School Holidays
    entities:
      - entity: sensor.schulferien
        name: Current Status
      - type: attribute
        entity: sensor.schulferien
        attribute: Next Holidays
        name: Name of the Holidays
      - type: attribute
        entity: sensor.schulferien
        attribute: Start
        name: Start of the Holidays
      - type: attribute
        entity: sensor.schulferien
        attribute: End
        name: End of the Holidays
      - type: attribute
        entity: sensor.schulferien
        attribute: Country
        name: Country
      - type: attribute
        entity: sensor.schulferien
        attribute: Region
        name: Region
      - type: attribute
        entity: sensor.schulferien
        attribute: Bridge Days
        name: Bridge Days

  - type: entities
    title: Public Holidays
    entities:
      - entity: sensor.feiertag
        name: Current Status
      - type: attribute
        entity: sensor.feiertag
        attribute: Next Public Holiday
        name: Name of the Public Holiday
      - type: attribute
        entity: sensor.feiertag
        attribute: Date of the Next Public Holiday
        name: Date of the Public Holiday
      - type: attribute
        entity: sensor.feiertag
        attribute: Country
        name: Country
      - type: attribute
        entity: sensor.feiertag
        attribute: Region
        name: Region

  - type: entities
    title: Combined School Holidays/Public Holidays
    entities:
      - entity: sensor.schulferien_feiertag
        name: Current Status
```

Here is a small card for the dashboard that explains the function of bridge days and lists the currently defined bridge days as an attribute:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: >
      **Bridge Days** are additional days that are counted as holiday days, even though they are not included in the API.
      These can be added in the `configuration.yaml`. Use the following format for that:

      ```yaml
      sensor:
        - platform: school_holidays
          name: "School Holidays Germany Lower Saxony"
          country_code: "DE"
          region: "DE-NI"
          bridge_days:
            - "10.05.2024"
            - "04.10.2024"
            - "01.11.2024"
      ```

      Each line in the `bridge_days` list must contain a date in the format `DD.MM.YYYY`.
  - type: markdown
    title: Currently Set Bridge Days
    content: >
      {% if state_attr('sensor.schulferien', 'Bridge Days') %}
      **Bridge Days:**
      {% for day in state_attr('sensor.schulferien', 'Bridge Days') %}
      - {{ day }}
      {% endfor %}
      {% else %}
      No bridge days defined.
      {% endif %}

```
