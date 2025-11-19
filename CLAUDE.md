# CLAUDE.md - AI Agent Development Guide for OpenWebRX+

## Cost Optimization & Efficient Development

**IMPORTANT - Cost Optimization:** Every call to the AI model API incurs a cost and requires electricity. Be smart and make as few requests as possible. Each request gets subsequently more expensive as the context increases.

### Efficient Development Practices

1. **Add learnings and gotchas to this file** to avoid repeating mistakes and trial & error
2. **Ignore line length and type errors until the very end**; use command line tools to fix those (black, flake8)
3. **Always prefer command line tools** to avoid expensive API requests (e.g., use git and jq instead of reading whole files)
4. **Use bulk operations and prefetch patterns** to minimize database queries

### Think Holistically

- What is the PURPOSE of this tool?
- Why is it failing on this issue?
- Is this a symptom of a larger architectural problem?
- Take a step back and analyze the root cause

### Development Best Practices

- **Commit often** - Small, focused commits are better than large monolithic ones
- **Use TDD whenever possible** - Write tests first, then implement
- **Keep it simple** - Always think hard and evaluate more complex approaches and alternative approaches before moving forward

---

## Project Overview

**OpenWebRX Plus (OpenWebRX+)** is an enhanced, multi-user Software Defined Radio (SDR) receiver with a web-based user interface. It allows multiple users to listen to and decode radio signals from SDR hardware over the internet simultaneously.

**Version:** 1.2.90
**License:** AGPL-3.0
**Language:** Python 3.5+
**Maintainer:** Marat Fayzullin (luarvique@gmail.com)
**Repository:** https://github.com/luarvique/openwebrxplus

### What Does This Do?

OpenWebRX+ turns SDR hardware (devices that can receive radio frequencies) into a web-accessible radio receiver that can:
- Display real-time waterfall and spectrum displays
- Demodulate analog modes (AM, FM, SSB, CW)
- Decode 30+ digital modes (FT8, APRS, DMR, D-Star, etc.)
- Decode specialized signals (ADSB aircraft, AIS ships, weather fax, SSTV images, pagers)
- Support multiple simultaneous users
- Record audio and decode signals in background
- Display received data on maps
- Scan bookmarked frequencies

---

## Architecture Overview

### Design Pattern
**MVC-like Architecture:**
- **Models:** Property-based reactive data system (`owrx/property/`)
- **Views:** HTML templates + JavaScript UI components (`htdocs/`)
- **Controllers:** HTTP request handlers (`owrx/controllers/`)

### Key Technologies
- **Backend:** Python 3.5+ with custom HTTP server
- **Real-time Communication:** WebSockets (custom implementation)
- **DSP Processing:** pycsdr (C library with Python bindings)
- **Frontend:** HTML5, JavaScript (jQuery), Bootstrap, Canvas/WebAudio APIs
- **Hardware Abstraction:** SoapySDR + custom connectors (owrx-connector)

### DSP Signal Flow
```
SDR Hardware → Source Connector → Selector → Demodulator Chain →
Client Audio Chain → Compression → WebSocket → Browser Audio/Display
```

---

## Directory Structure

### Core Application
- **`/owrx/`** - Main Python package (143 files)
  - `controllers/` - HTTP request handlers
  - `source/` - SDR hardware drivers (27 different SDR types)
  - `property/` - Reactive property system
  - `config/` - Configuration management
  - `service/` - Background services
  - `form/` - Form generation and validation
  - `reporting/` - External integrations (PSK Reporter, WSPRNet, MQTT)
  - `aprs/`, `audio/`, `web/`, `admin/`, `log/`, `dsame3/` - Feature modules

### Frontend
- **`/htdocs/`** - Web interface
  - HTML templates (index.html, settings.html, map.html, etc.)
  - `/lib/` - JavaScript modules (~62 files)
  - `/css/` - Stylesheets and themes
  - `/gfx/` - Images and icons

### DSP & Signal Processing
- **`/csdr/`** - DSP chains and processing modules
  - `chain/` - Demodulator chains (analog, digital, FFT)
  - `module/` - Specialized decoders (DRM, FreeDV, M17, etc.)

### Configuration & Data
- **`/bookmarks.d/`** - Pre-configured frequency bookmarks
- **`/debian/`** - Debian packaging
- **`/systemd/`** - Service definitions
- **`/test/`** - Unit tests (primarily property system)

### Build & Deployment
- **`buildall.sh`** - Build all packages from source
- **`docker.sh`** - Docker image builder
- **`/attic/docker/`** - Docker configurations

---

## Key Python Modules

### Entry Points
- **`openwebrx.py`** - Main entry point (simple wrapper)
- **`owrx/__main__.py`** - Application startup, HTTP server init
- **`setup.py`** - Python package installation

### Core Modules
- **`owrx/http.py`** - HTTP routing and request handling
- **`owrx/dsp.py`** (916 lines) - DSP processing chains, demodulator management
- **`owrx/modes.py`** - Demodulation mode definitions
- **`owrx/sdr.py`** - SDR source management
- **`owrx/connection.py`** - WebSocket connection management
- **`owrx/websocket.py`** - WebSocket protocol implementation

### Feature & Hardware
- **`owrx/feature.py`** - Runtime feature detection (checks for external programs)
- **`owrx/source/*.py`** - Individual SDR drivers (RTL-SDR, HackRF, SDRplay, etc.)
- **`owrx/soapy.py`** - SoapySDR integration

### Signal Processing & Decoders
- **`owrx/fft.py`** - FFT for waterfall display
- **`owrx/waterfall.py`** - Waterfall visualization
- **`owrx/wsjt.py`** - WSJT-X modes (FT8, FT4, WSPR, etc.)
- **`owrx/js8.py`** - JS8Call support
- **`owrx/pocsag.py`** - POCSAG pager decoder
- **`owrx/fax.py`** - Weather fax decoder
- **`owrx/sstv.py`** - SSTV image decoder

---

## Supported Hardware (27 SDR Types)

RTL-SDR, SDRplay (RSP1/RSP2/RSPduo/RSPdx), HackRF, Airspy (R2/Mini/HF+), LimeSDR, PlutoSDR, Perseus, RadioBerry, BladeRF, HydraSDR, FiFi-SDR, HPSDR, UHD (Ettus), FunCube Dongle Pro+, Red Pitaya, SDRangel, and more via SoapySDR.

---

## Supported Modes & Decoders

### Analog
AM, FM, WFM, NFM, USB, LSB, CW, DSB

### Digital Voice
DMR, YSF, D-Star, NXDN (via digiham), FreeDV (codec2), M17

### Digital Data
FT8, FT4, WSPR, JT65, JT9, FST4, FST4W, Q65, JS8Call, BPSK31/63, RTTY, SITOR-B, CW

### Specialized Decoders
- **APRS** - Packet radio
- **POCSAG** - Pagers
- **AIS** - Maritime
- **ADSB, VDL2, HFDL** - Aviation
- **ACARS** - Aviation data
- **SSTV, FAX** - Images
- **RDS** - FM radio data
- **ISM** - rtl-433 (weather stations, tire pressure, etc.)
- **EAS/SAME** - Emergency alerts
- **SELCALL** - DTMF, EEA, EIA, CCIR, ZVEY
- **DAB** - Digital audio broadcasting
- **HD Radio** - NRSC-5
- **DRM** - Digital Radio Mondiale

---

## Extension Points

### Adding New Features
- **New SDR drivers:** Add to `/owrx/source/`, inherit from `SdrSource`
- **New decoders:** Add to `/csdr/chain/` or `/csdr/module/`
- **New controllers:** Add to `/owrx/controllers/`, update `/owrx/http.py` routes
- **New UI components:** Add to `/htdocs/lib/`
- **New bookmarks:** Add JSON files to `/bookmarks.d/`

---

## Testing

**Framework:** Python unittest
**Location:** `/test/`
**Coverage:** Primarily property system validation (21 test modules)

**Run tests:**
```bash
python3 -m pytest test/
```

---

## Common Commands

### Build from source
```bash
./buildall.sh
```

### Run development server
```bash
python3 openwebrx.py
```

### Check feature availability
```bash
python3 -m owrx.feature
```

### Code formatting & linting
```bash
black owrx/ csdr/ test/
flake8 owrx/ csdr/ test/
```

---

## Configuration

### Modern (Recommended)
Web-based configuration at `http://localhost:8073/settings`
Stored in: `/var/lib/openwebrx/`

### Legacy (Deprecated)
`config_webrx.py` - Python configuration file (being phased out)

### Migration
Automatic migration from old to new config format on first run.

---

## Gotchas & Learnings

### Property System
- Properties are reactive and use a stack/layer system
- Changes propagate through property wiring
- Validators run on property updates
- Property deletion behavior can be tricky (see tests)

### DSP Chains
- Complex inheritance hierarchy
- Chain construction order matters
- Some chains require specific external programs

### WebSocket Protocol
- Custom binary protocols for audio/FFT data
- Different message types for different data streams
- Connection lifecycle management is critical

### Feature Detection
- Runtime checks for external programs
- Missing features disable corresponding modes
- Check with `owrx.feature` module

### SDR Hardware
- Each SDR type has unique quirks
- Sample rate and frequency range limitations
- Some SDRs require specific driver versions

---

## Detailed Documentation

For more detailed information about specific subsystems, see `docs/claude/`:
- **architecture.md** - Detailed architecture and design patterns
- **modules.md** - Module-by-module breakdown
- **dsp-chains.md** - DSP processing pipeline details
- **property-system.md** - Reactive property system
- **websocket-protocol.md** - WebSocket communication
- **sdr-drivers.md** - SDR hardware integration
- **decoders.md** - Digital mode decoders
- **frontend.md** - JavaScript UI components
- **configuration.md** - Configuration system
- **testing.md** - Testing infrastructure
