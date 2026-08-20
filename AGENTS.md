# AGENTS.md — Schulferien Integration

## Projekt
Home Assistant Custom Component: Schulferien & Feiertage via OpenHolidaysAPI.
HACS-ready, Python, domain `schulferien`.

## Commands
```
source venv/bin/activate          # venv aktivieren
pytest                            # Tests (root, pytest.ini konfiguriert)
pytest tests/test_xxx.py          # einzelne Datei
pytest -x --tb=short              # schnell fehlschlagend
pylint custom_components/schulferien --max-line-length=100  # Lint (Default-Config, kein .pylintrc)
```

`pytest.ini`: `pythonpath = custom_components/schulferien`, `asyncio_mode = auto`.
`pytest-homeassistant-custom-component` als Test-Framework.

## Integration-Funktion
Die Integration bietet Schulferien- und Feiertags-Informationen für Deutschland, Österreich und die Schweiz.

**Sensoren (4):**
- Schulferien heute/morgen — Status (ferientag/kein_ferientag) + nächste Ferien
- Feiertag heute/morgen — Status (Feiertag/kein_feiertag) + nächster Feiertag

**BinarySensoren (6):**
- Kombiniert (Schulferien ODER Feiertage), nur Schulferien, nur Feiertage — jeweils heute + morgen

**Konfiguration:**
- 2-Schritt-Flow: Land wählen → Region wählen (API-lookup)
- Multiple Instanzen möglich (verschiedene Länder/Regionen)
- Brückentage konfigurierbar via `bridge_days.yaml`

## Architektur (entry points)
- `custom_components/schulferien/__init__.py` — `async_setup_entry` / `async_unload_entry` (forwardet zu sensor + binary_sensor)
- `custom_components/schulferien/config_flow.py` — 2-Schritt-Flow: Land → Region (API-lookup)
- `custom_components/schulferien/sensor.py` — `async_setup_entry` für Sensoren (erstellt 4 Sensor-Instanzen)
- `custom_components/schulferien/binary_sensor.py` — `async_setup_entry` für 6 BinarySensoren
- `custom_components/schulferien/schulferien_sensor.py` — `SchulferienSensor`, `SchulferienMorgenSensor`
- `custom_components/schulferien/feiertag_sensor.py` — `FeiertagSensor`, `FeiertagMorgenSensor`
- `custom_components/schulferien/api_utils.py` — `fetch_data`, `parse_daten`, `load_bridge_days`, `compute_region_slug`

## Wichtige Konventionen
- **Entity IDs**: `sensor.schulferien_{land}_{region_slug}` — Ländercode (de/at/ch) + Regions-Slug (by/bw/he)
- **Unique IDs**: `schulferien_{land}_{region_slug}` — gleiche Struktur, ohne Prefix
- **API**: OpenHolidaysAPI mit Fallback-URLs (`const.py`). Tägliches Update um 03:00 via `async_track_time_change`.
- **Brückentage**: `bridge_days.yaml` im Modulverzeichnis, wird bei Sensor-Setup geladen.
- **Ostersonntag**: `feiertag_sensor.py` ergänzt Ostersonntag automatisch per Gauss-Formel (sprachunabhängig, je Jahr im Abruf-Fenster).
- **Multiple Instanzen**: Integration kann mehrfach installiert werden (verschiedene Länder/Regionen) — eindeutige IDs basieren auf Land+Region-Slug.
- **pylint**: keine `.pylintrc` — CI nutzt Default-Config; max-line 100 via `--max-line-length=100`.
- **Translations**: `translations/` mit de, en, nl, tr, da, pt, es, it, fr.

## Tests
- `tests/` — ~360 Test-Funktionen (342 gezählt, parametrisiert ~360)
- Tests mocken Home Assistant via `MagicMock`/`AsyncMock`, keine `homeassistant` Runtime nötig
- **Test-Qualitätsregel**: Tests verify intent, not just behavior. Tests must encode WHY behavior matters, not just WHAT it does.

## Gotchas
- **Fetch-Guard**: `async_update` lädt nur 1×/Tag bei Fehlschlag bzw. 1 Woche nach Erfolg, jeweils ab 03:00. `letzter_versuch` wird VOR dem Request gesetzt, `letztes_update` erst nach erfolgreicher Verarbeitung (Ordnung = Fehlschlags-Beweis).
- BinarySensoren lesen States über `hass.states.get()` (Polling bleibt) + State-Subscription (`async_track_state_change_event`) + Registry-Lookup (`async_get_entity_id`) in `async_added_to_hass` — Fallback auf konstruierte IDs; Cleanup via `async_will_remove_from_hass`
- `compute_region_slug()` strippt Länderpräfix von Region-Codes (z.B. `DE-BY` → `BY`)
- **make_add_entities Closure-Bug**: `entities_list=entities` Default + `entities` Closure-Variable = unterschiedliche Objekte. Korrekt: `entities.extend(entities_list)`
- **BinarySensor unique_id-Präfix** (Altbestand, bewusst NICHT geändert): BinarySensoren tragen den Domain-Präfix in der unique_id (z.B. `binary_sensor.schulferien_feiertage_DE_RP`), die Sensoren nicht (`schulferien_DE_RP`). Besteht seit v1.0 (Commit `9cc7388`, Feb 2025), auch in Release 1.2/main und 1.21. Funktionell harmlos (HA behandelt unique_id als opaken String). Ein Fix wäre ein Breaking Change für Bestandsinstallationen (Entities würden als neu registriert) → so lassen.
- **Nur-Sensoren einseitig (bewusst, kein exklusives Verhalten)**: Die 4 „Nur“-Sensoren (Schulferien/Feiertag × heute/morgen) prüfen jeweils nur eine Seite. Ein Feiertag in den Ferien ist weiterhin Feiertag UND Ferien — an beides-Tagen sind beide „Nur“-Sensoren an. Nicht zu exklusiver Logik ändern.
