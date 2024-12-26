# home-assistant-schulferien

Home Assistant-Integration, um Schulferien mithilfe der OpenHolidays-API als Entität für Automationen verfügbar zu machen. Zur Zeit noch auf eigene Gefahr verwenden, da ich hier auch viel über Home Assistant und Integrationen lerne. Die Releases sind getestet und funktionieren.

## Installation

### Manuell über HACS

1. Füge diesen Github Pfad in HACS -> Benutzerdefinierte Repositories hinzu

2. Suche nach "Schulferien" und lade den letzten Release herunter

3. Starte Home Assistant neu

4. Füge die Integration unter Einstellungen -> Geräte & Dienste -> + Integration hinzufügen -> "Schulferien" hinzu.

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
        attribute: Name der Ferien
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
        attribute: Name Feiertag
        name: Name des Feiertags
      - type: attribute
        entity: sensor.feiertag
        attribute: Datum
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
      - entity: sensor.schulferien_feiertage_kombiniert
        name: Aktueller Status
```

## Deinstallation

1. Entferne "Schulferien" unter Einstellungen -> Geräte & Dienste

2. Lösche den Ordner Schulferien unter custom_components

## ENGLISH

Home Assistant integration to make school holidays available as entities for automations using the OpenHolidays API. Use at your own risk for now, as I am still learning a lot about Home Assistant and integrations. The releases have been tested and they work.

## Installation-EN

### Manual with HACS

1. Add this GitHub path to HACS -> Custom Repositories.

2. Search for "Schulferien" and download the latest release.

3. Restart Home Assisttant.

4. Add the integration under Settings -> Devices & Services -> + Add Integration -> "Schulferien".

Create a simple entity card that displays all attributes on your dashboard with the following code. If necessary, the stack can be reduced to show only the desired information.

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
        attribute: Name der Ferien
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
        attribute: Name Feiertag
        name: Name des Feiertags
      - type: attribute
        entity: sensor.feiertag
        attribute: Datum
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
      - entity: sensor.schulferien_feiertage_kombiniert
        name: Aktueller Status
```

## Uninstall

1. Remove "Schulferien" under Settings -> Devices & Services

2. Delete the folder Schulferien under custom_components
