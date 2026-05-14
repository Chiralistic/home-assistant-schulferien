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
pylint custom_components/schulferien  # Lint (.pylintrc im Modulverzeichnis)
```

`pytest.ini`: `pythonpath = custom_components/schulferien`, `asyncio_mode = auto`.
`pytest-homeassistant-custom-component` als Test-Framework.

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
- **Ostersonntag-Workaround**: `feiertag_sensor.py` ergänzt Ostersonntag automatisch bei Ostermontag.
- **Multiple Instanzen**: Integration kann mehrfach installiert werden (verschiedene Länder/Regionen) — eindeutige IDs basieren auf Land+Region-Slug.
- **pylint**: `.pylintrc` in `custom_components/schulferien/` — sehr viele Checks disabled, max-line 100.
- **Translations**: `translations/` mit de, en, nl, tr, da, pt, es, it, fr.

## Tests
- `tests/` — 14 Testdateien, ~360 Tests
- Tests mocken Home Assistant via `MagicMock`/`AsyncMock`, keine `homeassistant` Runtime nötig
- `test_api_utils.py` hat die meisten Tests (fetch_data + parse_daten)
- Tests sind KI-generiert (siehe README)
- **Test-Qualitätsregel**: Tests verify intent, not just behavior. Tests must encode WHY behavior matters, not just WHAT it does. A test that can't fail when business logic changes is wrong.

## Gotchas
- `sensor.py` erstellt alle Sensoren innerhalb eines gemeinsamen `aiohttp.ClientSession` — beide Sensoren teilen sich die Session für initiale Updates
- BinarySensoren lesen States anderer Entities über `hass.states.get()` — Abhängigkeitsreihenfolge beim Setup beachten
- `compute_region_slug()` strippt Länderpräfix von Region-Codes (z.B. `DE-BY` → `BY`)
- **make_add_entities Closure-Bug**: `entities_list=entities` Default + `entities` Closure-Variable = unterschiedliche Objekte. Korrekt: `entities.extend(entities_list)`

## Gefundene Bugs (Analyse)
### Bug 1: `feiertag_sensor.py:321` — Crash bei `None`-Liste
- `self._referenzsensor._feiertags_info.get("feiertage_liste", [])` gibt `None` zurück wenn Key existiert aber `None` ist
- `TypeError: 'NoneType' object is not iterable` beim Durchlaufen der for-Schleife
- Fix: `.get("feiertage_liste") or []` ✅ Fixed

### Bug 2: `sensor.py:39,51` — Entity ID verwendet rohen Region-Code
- `instance_prefix = f"{land}_{region}".upper()` → z.B. "DE_DE-BY" wenn region="DE-BY"
- Entity ID: `sensor.schulferien_de_de-by` (doppeltes Länderpräfix)
- Sensor-Klassen verwenden `compute_region_slug()` → `sensor.schulferien_de_by`
- Fix: `compute_region_slug()` für Entity ID in sensor.py verwenden ✅ Fixed

### Bug 2a: `binary_sensor.py:333-336` — Gleicher Problem wie Bug 2
- Gleiche Logik wie sensor.py: roher Region-Code in Entity ID
- Fix: `compute_region_slug()` für Entity IDs in binary_sensor.py async_setup_entry verwenden ✅ Fixed

### Bug 3: `api_utils.py:104` — Crash bei leerer YAML-Datei
- `yaml.safe_load()` gibt `None` für leere/Whitespace-only YAML-Dateien zurück
- `.get("bridge_days", [])` auf `None` → `AttributeError`
- Fix: `bridge_days_config = yaml.safe_load(content) or {}` ✅ Fixed

### Bug 4: `sensor.py:34,45` — unique_id verwendet rohen Region-Code (doppeltes Land)
- `unique_id = f"schulferien_{instance_prefix}"` → "schulferien_DE_DE-BY"
- Soll: "schulferien_DE_BY" (konsistent mit entity_id und Sensor-Klassen)
- Fix: `f"schulferien_{land.upper()}_{region_slug}"` ✅ Fixed

### Bug 5: `tests/test_sensor.py:949-952` — Closure-Bug in make_add_entities
- `def add(entities_list=entities): entities_list.extend(entities)` — Default und Closure-Variable sind unterschiedliche Objekte
- `add([e1,e2])` → `[e1,e2].extend(added_entities)` → added_entities bleibt leer
- Fix: `def add(entities_list): entities.extend(entities_list)` ✅ Fixed

## Phasen-Plan
### Phase 4: Code-Kommentare
- Alle Quelldateien ausführlich kommentieren (Docstrings + Inline-Kommentare)
- binary_sensor.py, config_flow.py, schulferien_sensor.py, feiertag_sensor.py, api_utils.py
- Kommentare erklären WARUM, nicht nur WAS

### Phase 5: Test-Qualität
- Alle Tests nach "verify intent, not just behavior" bewerten
- Tests die nur WHAT testen aber nicht WARUM → verbessern
- Tests die bei Business-Logic-Änderungen nicht fehlschlagen können → identifizieren und fixen

## Sitzungs-Status
- Phase 1: ✅ Completed — Bugfixes (3 Bugs, 4 Tests aktualisiert, 360/360 bestanden)
- Phase 2: ✅ Completed — Gescappte Tests reaktiviert (360/360 bestanden)
- Phase 3: ✅ Completed — Pylint bereinigt (9.88/10, redundante Kommentare entfernt)
- Phase 3b: ✅ Completed — sensor.py unique_id fix (DE_DE-BY → DE_BY), sensor.py Docstrings + Kommentare, test_sensor.py Closure-Bug fix
- Phase 4: ✅ Completed — Docstrings + "WARUM"-Kommentare in allen 7 Quelldateien
- Phase 5: ✅ Completed — Test-Qualitätsaudit aller 8 Testdateien (360/360 bestanden)
  - test_config_flow.py: 45 Tests — Full-Flow-Integrationstests sind WHY-Tests, Einzelschritt-Tests WHAT für deterministische Logik
  - test_schulferien_sensor.py: 48 Tests — Morgen-Sensor-Tests + parametrisierte Tests + "not_sorted" sind WHY-Tests
  - test_binary_sensor.py: 71 Tests — OR/AND-Logik-Tests sind WHY-Tests
  - test_feiertag_sensor.py: 72 Tests — Ostersonntag-Workaround-Tests sind WHY-Tests
  - test_api_utils.py: 64 Tests — Error-Handling-Tests WHAT für deterministische Transformationen
  - test_sensor.py: 43 Tests — Full-Flow-Tests sind WHY-Tests
  - test_init.py: 3 Tests — Triviale Forwarding-Logik, WHAT-Tests akzeptabel
  - tests/__init__.py: Leer, kein Audit nötig
