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
- **Entity IDs**: `sensor.schulferien_{land}_{region}` — Ländercode (de/at/ch) + Regionscode (ni/by/bw/at-1)
- **API**: OpenHolidaysAPI mit Fallback-URLs (`const.py`). Tägliches Update um 03:00 via `async_track_time_change`.
- **Brückentage**: `bridge_days.yaml` im Modulverzeichnis, wird bei Sensor-Setup geladen.
- **Ostersonntag-Workaround**: `feiertag_sensor.py` ergänzt Ostersonntag automatisch bei Ostermontag.
- **Multiple Instanzen**: Integration kann mehrfach installiert werden (verschiedene Länder/Regionen) — eindeutige IDs basieren auf Land+Region.
- **pylint**: `.pylintrc` in `custom_components/schulferien/` — sehr viele Checks disabled, max-line 100.
- **Translations**: `translations/` mit de, en, nl, tr, da, pt, es, it, fr.

## Tests
- `tests/` — 7 Testdateien, ~400+ Tests
- Tests mocken Home Assistant via `MagicMock`/`AsyncMock`, keine `homeassistant` Runtime nötig
- `test_api_utils.py` hat die meisten Tests (fetch_data + parse_daten)
- Tests sind KI-generiert (siehe README)

## Gotchas
- `sensor.py` erstellt alle Sensoren innerhalb eines gemeinsamen `aiohttp.ClientSession` — beide Sensoren teilen sich die Session für initiale Updates
- BinarySensoren lesen States anderer Entities über `hass.states.get()` — Abhängigkeitsreihenfolge beim Setup beachten
- `compute_region_slug()` strippt Länderpräfix von Region-Codes (z.B. `DE-BY` → `BY`)

## Gefundene Bugs (Analyse)
### Bug 1: `feiertag_sensor.py:321` — Crash bei `None`-Liste
- `self._referenzsensor._feiertags_info.get("feiertage_liste", [])` gibt `None` zurück wenn Key existiert aber `None` ist
- `TypeError: 'NoneType' object is not iterable` beim Durchlaufen der for-Schleife
- Fix: `.get("feiertage_liste") or []`

### Bug 2: `sensor.py:39,51` — Entity ID verwendet rohen Region-Code
- `instance_prefix = f"{land}_{region}".upper()` → z.B. "DE_DE-BY" wenn region="DE-BY"
- Entity ID: `sensor.schulferien_de_de-by` (doppeltes Länderpräfix)
- Sensor-Klassen verwenden `compute_region_slug()` → `sensor.schulferien_de_by`
- Fix: `compute_region_slug()` für Entity ID in sensor.py verwenden

### Bug 2a: `binary_sensor.py:333-336` — Gleicher Problem wie Bug 2
- Gleiche Logik wie sensor.py: roher Region-Code in Entity ID
- Fix: `compute_region_slug()` für Entity IDs in binary_sensor.py async_setup_entry verwenden

### Bug 3: `api_utils.py:104` — Crash bei leerer YAML-Datei
- `yaml.safe_load()` gibt `None` für leere/Whitespace-only YAML-Dateien zurück
- `.get("bridge_days", [])` auf `None` → `AttributeError`
- Fix: `bridge_days_config = yaml.safe_load(content) or {}`

## Phasen-Plan
### Phase 1: Bugfixes
1. `feiertag_sensor.py:321`: `.get("feiertage_liste", [])` → `.get("feiertage_liste") or []`
2. `api_utils.py:104`: `yaml.safe_load(content)` → `yaml.safe_load(content) or {}`
3. `sensor.py:39,51`: Entity IDs mit `compute_region_slug()` erstellen
4. `binary_sensor.py:333-336`: Entity IDs mit `compute_region_slug()` erstellen

### Phase 2: Tests
- Bestehende Tests laufen lassen
- Gescappte Tests reaktivieren
- Neue Tests für Entity-ID-Korrektheit

### Phase 3: Pylint
- Pylint laufen lassen
- Top-Fehler beheben
- Score verbessern

## Sitzungs-Status
- Phase 1: ✅ Completed — Alle 3 Bugs gefixt, 4 Tests aktualisiert, 360/360 Tests bestanden
  - Bug 1: `feiertag_sensor.py:321` — `.get("feiertage_liste") or []`
  - Bug 2: `sensor.py:39,51` — Entity IDs mit `compute_region_slug()`
  - Bug 2a: `binary_sensor.py:333-336` — Entity IDs mit `compute_region_slug()`
  - Bug 3: `api_utils.py:104` — `yaml.safe_load(content) or {}`
  - Bonus: `compute_region_slug()` handhabt nun `None`-region
  - Tests: 4 Tests aktualisiert für neues Entity-ID-Format
- Phase 2: ✅ Completed — 4 gescappte Tests reaktiviert, try/except/skip Cleanup
  - `test_feiertag_morgen_sensor_native_value_none_list` — Bug 1 Fix, skip entfernt
  - `test_load_bridge_days_empty_file` — try/except/skip entfernt
  - `test_load_bridge_days_valid_content` — try/except/skip entfernt
  - `test_load_bridge_days_yaml_error` — try/except/skip entfernt
  - `test_load_bridge_days_file_not_found` — Docstring bereinigt
  - 360/360 Tests bestanden
- Phase 3: ✅ Completed — Pylint 9.88/10 (+0.21), redundante Kommentare entfernt
  - `__init__.py` — English docstring → German
  - `const.py` — Kommentar-Lines ergänzt
  - `config_flow.py` — 12 redundante Inline-Kommentare entfernt, Datei bereinigt
  - `sensor.py` — 10 redundante Inline-Kommentare entfernt
  - `binary_sensor.py` — "NEU:"-Kommentare bereinigt, Setup-Kommentare verbessert
  - `schulferien_sensor.py` — 8 redundante Kommentare entfernt
  - `feiertag_sensor.py` — 10 redundante Kommentare entfernt
  - 360/360 Tests bestanden
