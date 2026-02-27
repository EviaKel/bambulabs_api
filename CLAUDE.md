# CLAUDE.md — bambulabs_api

This file provides context for AI assistants working on this codebase.

## Project Overview

`bambulabs_api` is a Python library that provides programmatic control and monitoring of BambuLab 3D printers. Communication happens over three protocols:

- **MQTT** (port 8883, TLS) — primary control and status channel
- **FTP/FTPS** (port 990, implicit TLS) — file upload/management
- **TCP** (port 6000) — live camera feed

**Current version**: 2.5.10
**Python requirement**: >= 3.10
**PyPI package**: `bambulabs_api`

---

## Repository Structure

```
bambulabs_api/
├── bambulabs_api/          # Main source package
│   ├── __init__.py         # Public API exports and version
│   ├── client.py           # Printer facade class (main entry point)
│   ├── mqtt_client.py      # MQTT protocol implementation
│   ├── camera_client.py    # TCP camera frame capture
│   ├── ftp_client.py       # Implicit FTPS file transfer
│   ├── filament_info.py    # Filament enums and dataclasses
│   ├── states_info.py      # PrintStatus and GcodeState enums
│   ├── printer_info.py     # NozzleType enum and nozzle constants
│   ├── ams.py              # AMS (multi-filament system) classes
│   └── py.typed            # PEP 561 type hints marker
├── tests/
│   └── test_client.py      # Unit tests (pytest)
├── docs/                   # Sphinx documentation source
│   ├── conf.py
│   ├── api/                # Per-class RST API reference files
│   ├── release/            # Per-version release notes (*.md)
│   └── compatibility/      # Printer model compatibility (CSV + RST)
├── examples/               # Usage examples
│   ├── Basic/              # Connection and subscription examples
│   ├── camera/             # Camera capture example
│   └── print/              # 3mf and gcode print examples
├── .github/workflows/      # CI/CD (flake8, pytest, publish, docs)
├── pyproject.toml          # Project metadata and dependencies
├── setup.py                # Legacy setuptools entry
├── requirements.txt        # Development dependencies
└── environment.yml         # Conda environment spec
```

---

## Key Modules

### `client.py` — `Printer` (Facade)

The primary entry point for users. Instantiates and coordinates all three sub-clients.

```python
printer = bl.Printer(ip_address="192.168.1.200", access_code="12345678", serial="AC12309BH109")
printer.connect()   # starts MQTT
printer.disconnect()
```

Key method groups:
- **Connection**: `connect()`, `disconnect()`, `mqtt_start()`, `mqtt_stop()`, `camera_start()`, `camera_stop()`
- **Status**: `get_state()` → `PrintStatus`, `get_percentage()`, `get_time()`
- **Temperature**: `get_bed_temperature()`, `get_nozzle_temperature()`, `set_bed_temperature()`, `set_nozzle_temperature()`
- **Lighting**: `turn_light_on()`, `turn_light_off()`, `get_light_state()`
- **Movement**: `home_printer()`, `move_z_axis()`
- **Print control**: `start_print()`, `pause_print()`, `resume_print()`, `stop_print()`, `skip_objects()`
- **Filament**: `load_filament_spool()`, `unload_filament_spool()`, `set_filament_printer()`, `retry_filament_action()`
- **G-code**: `gcode()`, `send_gcode()`
- **Files**: `upload_file()`, `delete_file()`
- **Camera**: `get_camera_frame()` (base64), `get_camera_image()` (PIL Image)
- **Speed/Fans**: `set_print_speed()`, `set_part_fan_speed()`, `set_aux_fan_speed()`, `set_chamber_fan_speed()`
- **AMS**: `ams_hub()` → `AMSHub`, `vt_tray()`
- **Diagnostics**: `mqtt_dump()`, `subtask_name()`, `print_error_code()`

### `mqtt_client.py` — `PrinterMQTTClient`

Low-level MQTT v3.1.1 handler. 877 lines. Manages the TLS connection, message parsing, and all command publishing.

- MQTT username: `"bblp"`, password: `access_code`
- Topics: `device/{serial}/request` (publish), `device/{serial}/report` (subscribe)
- TLS on, but certificate validation is disabled (printer uses self-signed cert)
- Uses the `@__ready` decorator internally to gate commands on connection state
- `is_valid_gcode(line: str) -> bool` is a utility function for G-code validation

### `camera_client.py` — `PrinterCamera`

Daemon-threaded TCP camera capture. Connects on port 6000, uses a binary auth protocol. Returns base64-encoded JPEG frames.

### `ftp_client.py` — `PrinterFTPClient`

Wraps `ImplicitFTP_TLS` (a custom `ftplib.FTP_TLS` subclass) for port 990 implicit SSL. Connection is managed via decorators.

### `filament_info.py`

- `Filament` enum — 20 filament types with temperature ranges and tray index info
- `AMSFilamentSettings` dataclass — per-spool configuration
- `FilamentTray` dataclass — represents a single AMS tray slot

### `states_info.py`

- `PrintStatus` enum — 36 states (PRINTING, IDLE, PAUSED_*, CALIBRAT*, error states, UNKNOWN)
- `GcodeState` enum — G-code execution states

### `ams.py`

- `AMSHub` — container for multiple AMS units, indexed by ID
- `AMS` — individual unit with temperature, humidity, and `FilamentTray` slots

---

## Development Setup

### Conda (recommended)

```bash
conda env create -f environment.yml
conda activate bl_api
pip install -e .
```

### pip only

```bash
pip install -r requirements.txt
pip install -e .
```

---

## Common Commands

| Task | Command |
|------|---------|
| Run tests | `pytest` |
| Lint | `flake8 --ignore=E501,E203,W503,F401 .` |
| Build docs | `python3 -m sphinx ./docs docs/build/html` |
| Install editable | `pip install -e .` |

---

## CI/CD Workflows

All workflows trigger on push/PR to `main` and `dev` branches.

| Workflow | File | Purpose |
|----------|------|---------|
| Lint | `flake8.yml` | flake8 on Python 3.10 |
| Tests | `pytest-unit-tests.yml` | pytest on Python 3.10 |
| Docs | `static.yml` | Sphinx build + GitHub Pages deploy |
| Publish | `publish.yml` | PyPI publish + Sigstore signing + GitHub Release (triggered by pyproject.toml version change on `main`) |

The publish workflow auto-creates a GitHub Release and reads release notes from `docs/release/{VERSION}-notes.md` if it exists.

---

## Code Conventions

### Style

- **PEP 8** with these flake8 exceptions: `E501` (line length), `E203` (whitespace before `:`), `W503` (line break before binary operator), `F401` (imported but unused — needed for re-exports)
- Snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants and enum members

### Type Hints

- Full type annotations throughout; modern Python 3.10+ union syntax (`str | int | None`, not `Optional[str]`)
- `py.typed` marker present — package is fully typed per PEP 561

### Docstrings

- NumPy-style with `Parameters`, `Returns`, and `Raises` sections
- Include type information and usage examples in docstrings

### Design Patterns

- **Facade**: `Printer` is a thin facade over `PrinterMQTTClient`, `PrinterCamera`, and `PrinterFTPClient`
- **Decorator**: `@__ready` gates MQTT commands; FTP uses connection decorators
- **Enums**: Use enums (`PrintStatus`, `Filament`, `NozzleType`, `GcodeState`) for all typed state — never raw strings or ints for these values
- **Threading**: MQTT and camera run on daemon threads; `Printer` methods are generally called from the main thread

### Adding New Printer Commands

1. Add the low-level method to `PrinterMQTTClient` (`mqtt_client.py`) with the MQTT JSON payload
2. Expose it through the `Printer` facade in `client.py`
3. Update `bambulabs_api/__init__.py` if new public types are introduced
4. Add an RST entry under `docs/api/` for Sphinx

### Adding New Enums / States

- Add to the appropriate file (`states_info.py`, `filament_info.py`, `printer_info.py`)
- Export from `__init__.py`
- Document in the corresponding `docs/api/*.rst` file

---

## Testing

Tests live in `tests/test_client.py`. Coverage is currently minimal (one test class, one test). When adding features, add corresponding tests.

```bash
pytest              # run all tests
pytest -v           # verbose output
pytest tests/       # explicit path
```

Tests do **not** require a real printer — mock or unit-test internal logic only.

---

## Versioning & Releases

Version is declared in `pyproject.toml` under `[project] version`. To release:

1. Bump the version in `pyproject.toml`
2. Create release notes at `docs/release/{VERSION}-notes.md`
3. Merge to `main` — the publish workflow handles PyPI + GitHub Release automatically

---

## Compatibility

Supported printer models are documented in `docs/compatibility/` (CSV + RST). Currently covers P1, A1, and X1 series. Check there before implementing model-specific behaviour.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `paho-mqtt` | >= 2.0.0 | MQTT protocol client |
| `pillow` | >= 11.0.0 | Camera image processing |

Dev-only: `pytest`, `flake8`, `sphinx`, `myst_parser`, `sphinx_rtd_theme`, `webcolors`
