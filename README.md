# home-assistant-schulferien

Home Assistant-Integration, um Schulferien mithilfe der OpenHolidays-API als Entität für Automationen verfügbar zu machen. Zur Zeit noch auf eigene Gefahr verwenden, da ich hier auch viel über Home Assistant und Integrationen lerne. Die Releases sind getestet und funktionieren.

## Mehrere Bundesländer/Länder gleichzeitig tracken

Die Integration kann mehrfach installiert werden, um Schulferien aus verschiedenen Bundesländern oder Ländern zu verfolgen. Jede Installation erzeugt automatisch eindeutige IDs basierend auf Land und Region:

```
sensor.schulferien_de_by   → Deutschland, Bayern

sensor.schulferien_de_bw   → Deutschland, Baden-Württemberg
sensor.schulferien_at_by   → Österreich, Burgenland
```

Jede Instanz hat eigene Sensoren für:
- **Schulferien** (`sensor.schulferien_{land}_{region}`) – aktueller Status
- **Schulferien Morgen** (`sensor.schulferien_{land}_{region}_morgen`) – Status für morgen
- **Feiertage** (`sensor.feiertag_{land}_{region}`) – nächster Feiertag
- **Binary Sensors** (`binary_sensor.schulferien_feiertage_{land}_{region}`, `binary_sensor.nur_schulferien_{land}_{region}`, `binary_sensor.nur_feiertage_{land}_{region}` — jeweils auch mit `_morgen`-Suffix) – kombinierte Zustände

### Update von älteren Versionen (vor Multi-Instanz-Unterstützung)

Mit der Multi-Instanz-Unterstützung haben sich die Entity-IDs **breaking** geändert:
aus `sensor.schulferien` wird z.B. `sensor.schulferien_de_rp` (Land/Region-abhängig),
analog `sensor.feiertag_*` und die Binary-Sensoren (`binary_sensor.schulferien_feiertage_de_rp`).

Beim Update bitte einmalig:

1. HomeAssistant neu starten.
2. Alte Entities (z.B. `sensor.schulferien`, `sensor.schulferien_morgen`) unter **Einstellungen → Geräte & Dienste → Entitäten** löschen — sie bleiben sonst als „nicht verfügbar" zurück, da die alten eindeutigen IDs nicht mehr erzeugt werden.
3. Automatisierungen/Dashboards auf die neuen Entity-IDs umstellen (siehe Beispiele oben).

Disclaimer: Die Tests für die Integration, die nicht mit in Home Assistant installiert werden, sind vollständig von KI gecoded worden.

## Installation

### Manuell über HACS

1. Nutze HACS

2. Suche nach "Schulferien" und lade den letzten Release herunter

3. Starte Home Assistant neu

4. Füge die Integration unter Einstellungen -> Geräte & Dienste -> + Integration hinzufügen -> "Schulferien" hinzu.

5. Warten: Nach der Einrichtung bzw. nach einem Home Assistant Neustart kann es bis zu 30s dauern bis alle Attribute und States aktualisiert sind.

Erstelle eine einfache Entitätskarte, die alle Attribute anzeigt in deinem Dashboard mit dem folgenden Code. Bei Bedarf kann der Stack verkleinert werden um nur die Informationen anzuzeigen, die gewünscht sind.

### Beispiel: Deutschland (Niedersachsen)

Dieses Beispiel zeigt die Entitäten für Niedersachsen. Passe die Entity-IDs (`sensor.schulferien_de_ni`, `sensor.feiertag_de_ni`, `binary_sensor.schulferien_feiertage_de_ni`) an das gewünschte Land und die Region an. Ersetze dabei `de` durch den Ländercode (z.B. `at` für Österreich, `ch` für die Schweiz) und `ni` durch den Regionscode (z.B. `by` für Bayern, `bw` für Baden-Württemberg).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Schulferien – Niedersachsen (Beispiel)
    entities:
      - entity: sensor.schulferien_de_ni
        name: Aktueller Status
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Name der Ferien
        name: Name der Ferien
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Beginn
        name: Beginn der Ferien
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Ende
        name: Ende der Ferien
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Land
        name: Land
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Region
        name: Region
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Brückentage
        name: Brückentage
  - type: entities
    title: Feiertage – Niedersachsen (Beispiel)
    entities:
      - entity: sensor.feiertag_de_ni
        name: Aktueller Status
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Name Feiertag
        name: Name des Feiertags
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Datum
        name: Datum des Feiertags
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Land
        name: Land
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Region
        name: Region
  - type: entities
    title: Kombiniert – Niedersachsen (Beispiel)
    entities:
      - entity: binary_sensor.schulferien_feiertage_de_ni
        name: Schulferien oder Feiertag (binary)
      - entity: binary_sensor.schulferien_feiertage_de_ni_morgen
        name: Morgen Schulferien oder Feiertag (binary)
      - entity: binary_sensor.nur_schulferien_de_ni
        name: Nur Schulferien (binary)
      - entity: binary_sensor.nur_schulferien_de_ni_morgen
        name: Nur Schulferien Morgen (binary)
      - entity: binary_sensor.nur_feiertage_de_ni
        name: Nur Feiertage (binary)
      - entity: binary_sensor.nur_feiertage_de_ni_morgen
        name: Nur Feiertage Morgen (binary)
```

### Mehrere Bundesländer gleichzeitig anzeigen

Um Schulferien aus mehreren Bundesländern anzuzeigen, füge einfach weitere Blöcke hinzu und passe die Entity-IDs an. Beispiel für Bayern und Baden-Württemberg:

| Bundesland | Länder-Code | Regions-Code | Entity-ID Schulferien |
|---|---|---|---|
| Bayern | `de` | `by` | `sensor.schulferien_de_by` |
| Baden-Württemberg | `de` | `bw` | `sensor.schulferien_de_bw` |
| Niedersachsen | `de` | `ni` | `sensor.schulferien_de_ni` |
| Österreich (Burgenland) | `at` | `at-1` | `sensor.schulferien_at_at_1` |

## Deinstallation

1. Entferne "Schulferien" unter Einstellungen -> Geräte & Dienste

2. Lösche den Ordner Schulferien unter custom_components

## ENGLISH

Home Assistant integration to make school holidays available as entities for automations using the OpenHolidays API. Use at your own risk for now, as I am still learning a lot about Home Assistant and integrations. The releases have been tested and they work.

## Multiple countries/regions at once

The integration can be installed multiple times to track school holidays from different states or countries. Each installation automatically generates unique IDs based on country and region:

```
sensor.schulferien_de_by   → Germany, Bavaria
sensor.schulferien_de_bw   → Germany, Baden-Württemberg
sensor.schulferien_at_by   → Austria, Burgenland
```

Each instance has its own sensors for:
- **School holidays** (`sensor.schulferien_{country}_{region}`) – current status
- **School holidays tomorrow** (`sensor.schulferien_{country}_{region}_morgen`) – status for tomorrow
- **Holidays** (`sensor.feiertag_{country}_{region}`) – next public holiday
- **Binary sensors** – combined states

### Example: Germany (Lower Saxony)

This example shows the entities for Lower Saxony. Adjust the entity IDs (`sensor.schulferien_de_ni`, `sensor.feiertag_de_ni`, `binary_sensor.schulferien_feiertage_de_ni`) to your desired country and region. Replace `de` with the country code (e.g., `at` for Austria, `ch` for Switzerland) and `ni` with the region code (e.g., `by` for Bavaria, `bw` for Baden-Württemberg).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: School holidays – Lower Saxony (example)
    entities:
      - entity: sensor.schulferien_de_ni
        name: Current status
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Name der Ferien
        name: Holiday name
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Beginn
        name: Start date
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Ende
        name: End date
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Land
        name: Country
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Region
        name: Region
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Brückentage
        name: Bridge days
  - type: entities
    title: Public holidays – Lower Saxony (example)
    entities:
      - entity: sensor.feiertag_de_ni
        name: Current status
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Name Feiertag
        name: Holiday name
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Datum
        name: Date
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Land
        name: Country
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Region
        name: Region
  - type: entities
    title: Combined – Lower Saxony (example)
    entities:
      - entity: binary_sensor.schulferien_feiertage_de_ni
        name: School holidays or public holiday
      - entity: binary_sensor.schulferien_feiertage_de_ni_morgen
        name: Tomorrow: school holidays or public holiday
      - entity: binary_sensor.nur_schulferien_de_ni
        name: Only school holidays
      - entity: binary_sensor.nur_schulferien_de_ni_morgen
        name: Tomorrow: only school holidays
      - entity: binary_sensor.nur_feiertage_de_ni
        name: Only public holidays
      - entity: binary_sensor.nur_feiertage_de_ni_morgen
        name: Tomorrow: only public holidays
```

### Track multiple states at once

To display school holidays from multiple states, simply add more blocks and adjust the entity IDs. Example for Bavaria and Baden-Württemberg:

| State | Country Code | Region Code | School holiday Entity ID |
|---|---|---|---|
| Bavaria | `de` | `by` | `sensor.schulferien_de_by` |
| Baden-Württemberg | `de` | `bw` | `sensor.schulferien_de_bw` |
| Lower Saxony | `de` | `ni` | `sensor.schulferien_de_ni` |
| Austria (Burgenland) | `at` | `at-1` | `sensor.schulferien_at_at_1` |

## Uninstall

1. Remove "Schulferien" under Settings -> Devices & Services

2. Delete the folder Schulferien under custom_components

Home Assistant integration to make school holidays available as entities for automations using the OpenHolidays API. Use at your own risk for now, as I am still learning a lot about Home Assistant and integrations. The releases are tested and work.

## Track multiple states/countries at once

The integration can be installed multiple times to track school holidays from different states or countries. Each installation automatically generates unique IDs based on country and region:

```
sensor.schulferien_de_by   → Germany, Bavaria

sensor.schulferien_de_bw   → Germany, Baden-Württemberg
sensor.schulferien_at_by   → Austria, Burgenland
```

Each instance has its own sensors for:
- **School holidays** (`sensor.schulferien_{country}_{region}`) – current status
- **School holidays tomorrow** (`sensor.schulferien_{country}_{region}_morgen`) – status for tomorrow
- **Public holidays** (`sensor.feiertag_{country}_{region}`) – next public holiday
- **Binary sensors** (`binary_sensor.schulferien_feiertage_{country}_{region}`, `binary_sensor.nur_schulferien_{country}_{region}`, `binary_sensor.nur_feiertage_{country}_{region}` — each also available with a `_morgen` suffix) – combined states

### Updating from older versions (before multi-instance support)

With multi-instance support, the entity IDs have changed in a **breaking** way:
e.g. `sensor.schulferien` becomes `sensor.schulferien_de_rp` (depending on country/region),
likewise `sensor.feiertag_*` and the binary sensors (`binary_sensor.schulferien_feiertage_de_rp`).

When updating, please do the following once:

1. Restart Home Assistant.
2. Delete old entities (e.g. `sensor.schulferien`, `sensor.schulferien_morgen`) under **Settings → Devices & Services → Entities** — otherwise they remain as "unavailable", because the old unique IDs are no longer generated.
3. Update your automations/dashboards to the new entity IDs (see examples above).

Disclaimer: The tests for the integration, which are not installed together with Home Assistant, have been completely coded by AI.

## Installation

### Manually via HACS

1. Use HACS

2. Search for "Schulferien" and download the latest release

3. Restart Home Assistant

4. Add the integration under Settings -> Devices & Services -> + Add integration -> "Schulferien".

5. Wait: After the setup or after a Home Assistant restart, it can take up to 30 seconds until all attributes and states are updated.

Create a simple entity card that shows all attributes in your dashboard using the following code. If needed, the stack can be reduced to display only the information you want.

### Example: Germany (Lower Saxony)

This example shows the entities for Lower Saxony. Adjust the entity IDs (`sensor.schulferien_de_ni`, `sensor.feiertag_de_ni`, `binary_sensor.schulferien_feiertage_de_ni`) to your desired country and region. Replace `de` with the country code (e.g. `at` for Austria, `ch` for Switzerland) and `ni` with the region code (e.g. `by` for Bavaria, `bw` for Baden-Württemberg).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: School holidays – Lower Saxony (example)
    entities:
      - entity: sensor.schulferien_de_ni
        name: Current status
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Name der Ferien
        name: Holiday name
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Beginn
        name: Start of the holidays
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Ende
        name: End of the holidays
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Land
        name: Country
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Region
        name: Region
      - type: attribute
        entity: sensor.schulferien_de_ni
        attribute: Brückentage
        name: Bridge days
  - type: entities
    title: Public holidays – Lower Saxony (example)
    entities:
      - entity: sensor.feiertag_de_ni
        name: Current status
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Name Feiertag
        name: Name of the public holiday
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Datum
        name: Date of the public holiday
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Land
        name: Country
      - type: attribute
        entity: sensor.feiertag_de_ni
        attribute: Region
        name: Region
  - type: entities
    title: Combined – Lower Saxony (example)
    entities:
      - entity: binary_sensor.schulferien_feiertage_de_ni
        name: School holidays or public holiday (binary)
      - entity: binary_sensor.schulferien_feiertage_de_ni_morgen
        name: Tomorrow: school holidays or public holiday (binary)
      - entity: binary_sensor.nur_schulferien_de_ni
        name: Only school holidays (binary)
      - entity: binary_sensor.nur_schulferien_de_ni_morgen
        name: Tomorrow: only school holidays (binary)
      - entity: binary_sensor.nur_feiertage_de_ni
        name: Only public holidays (binary)
      - entity: binary_sensor.nur_feiertage_de_ni_morgen
        name: Tomorrow: only public holidays (binary)
```

### Display multiple states at once

To display school holidays from multiple states, simply add more blocks and adjust the entity IDs. Example for Bavaria and Baden-Württemberg:

| State | Country Code | Region Code | School holiday Entity ID |
|---|---|---|---|
| Bavaria | `de` | `by` | `sensor.schulferien_de_by` |
| Baden-Württemberg | `de` | `bw` | `sensor.schulferien_de_bw` |
| Lower Saxony | `de` | `ni` | `sensor.schulferien_de_ni` |
| Austria (Burgenland) | `at` | `at-1` | `sensor.schulferien_at_at_1` |

## Uninstall

1. Remove "Schulferien" under Settings -> Devices & Services

2. Delete the folder Schulferien under custom_components
