# OpenWebRX+ Module Reference

## Core Entry Points

### `openwebrx.py`
**Type:** Main entry point
**Lines:** ~10
**Purpose:** Simple wrapper that imports and runs the main application

### `owrx/__main__.py`
**Type:** Application bootstrap
**Lines:** ~300
**Key Functions:**
- `main()` - Application entry point
- Signal handler setup (SIGTERM, SIGINT)
- HTTP server initialization
- Configuration loading
- Daemon mode support

### `setup.py`
**Type:** Package installer
**Purpose:** Python package definition for pip/setuptools installation

---

## HTTP & Routing

### `owrx/http.py`
**Type:** HTTP server and router
**Lines:** ~500
**Key Classes:**
- `Router` - URL routing (static and regex)
- `RequestHandler` - HTTP request handler
- `Request` - Request wrapper with parsed data

**Routes Defined:**
- `/` → `ReceiveController` (main interface)
- `/static/` → `AssetsController` (static files)
- `/settings/` → Various settings controllers
- `/api/` → `ApiController` (REST API)
- `/ws/` → `WebSocketController` (WebSocket upgrade)
- `/map` → `MapController` (map display)
- `/login` → `SessionController` (authentication)
- `/metrics` → `MetricsController` (Prometheus metrics)
- `/files/` → `FilesController` (file browser)

### `owrx/controllers/` Directory

#### `owrx/controllers/assets.py`
**Type:** Static asset handler
**Classes:**
- `OwrxAssetsController` - Serves static files
- `AprsSymbolsController` - APRS symbol images
- `CompiledAssetsController` - Minified/compiled assets

#### `owrx/controllers/api.py`
**Type:** REST API endpoints
**Endpoints:**
- `/api/status` - Server status
- `/api/features` - Available features
- `/api/receivers` - Receiver list
- `/api/profiles` - Profile list

#### `owrx/controllers/websocket.py`
**Type:** WebSocket handler
**Purpose:** Upgrades HTTP connection to WebSocket, initializes real-time connection

#### `owrx/controllers/session.py`
**Type:** Authentication
**Purpose:** Login, logout, session management

#### `owrx/controllers/admin.py`
**Type:** Admin panel
**Purpose:** User management, system configuration, logs

#### `owrx/controllers/clients.py`
**Type:** Client monitoring
**Purpose:** Display connected clients

#### `owrx/controllers/settings/` Directory
Settings management for different aspects:
- `general.py` - General receiver settings
- `sdr.py` - SDR device configuration
- `decoding.py` - Decoder settings
- `reporting.py` - External reporting (PSK Reporter, etc.)
- `bookmarks.py` - Bookmark management

---

## WebSocket & Connection Management

### `owrx/websocket.py`
**Type:** WebSocket protocol implementation
**Lines:** ~400
**Key Classes:**
- `WebSocketConnection` - WebSocket connection handler
- `WebSocketMessageHandler` - Message parsing/routing

**Message Types Handled:**
- `dspcontrol` - DSP parameter changes (frequency, mode, etc.)
- `config` - Configuration requests
- `connectionproperties` - Client capabilities
- `chat` - User chat messages
- `audiostart`/`audiostop` - Audio streaming control

### `owrx/connection.py`
**Type:** Client connection manager
**Lines:** ~800
**Key Classes:**
- `OpenWebRxReceiverClient` - Per-client connection handler
- Manages DSP chains, audio streaming, waterfall generation

**Responsibilities:**
- Client lifecycle (connect, disconnect)
- DSP chain per client
- Waterfall FFT generation
- Audio compression and streaming
- Metadata distribution

---

## DSP & Signal Processing

### `owrx/dsp.py`
**Type:** DSP chain management
**Lines:** 916
**Key Classes:**
- `DspManager` - Manages all DSP chains for a receiver
- `CsdrDspChain` - Base DSP chain
- `SpectrumDspChain` - FFT processing
- `AudioDspChain` - Audio output chain

**Chain Types:**
- Primary chain (main receiver)
- Secondary chains (background decoders)
- Audio chains (per client)

### `csdr/chain/` Directory
Demodulator chain implementations:

#### `csdr/chain/analog.py`
**Demodulators:** AM, FM, SSB (USB/LSB), CW, DSB

#### `csdr/chain/digimodes.py`
**Demodulators:** BPSK31, BPSK63, RTTY

#### `csdr/chain/ft8.py`
**Demodulators:** FT8, FT4, FT8-Wide, FT4-Wide

#### `csdr/chain/wsjt.py`
**Demodulators:** WSPR, JT65, JT9, FST4, FST4W, Q65

#### `csdr/chain/digiham.py`
**Demodulators:** DMR, YSF, D-Star, NXDN

#### `csdr/chain/freedv.py`
**Demodulators:** FreeDV (various modes)

#### `csdr/chain/m17.py`
**Demodulators:** M17

#### `csdr/chain/drm.py`
**Demodulators:** DRM (Digital Radio Mondiale)

#### `csdr/chain/fft.py`
**Purpose:** FFT processing for waterfall

### `csdr/module/` Directory
Specialized processing modules:
- `csdr/module/js8.py` - JS8Call decoder
- `csdr/module/direwolf.py` - APRS decoder
- `csdr/module/rtl433.py` - ISM band decoder
- `csdr/module/multimon.py` - Multi-mode decoder (POCSAG, EAS, SELCALL)
- `csdr/module/dump1090.py` - ADSB decoder
- `csdr/module/aircraft.py` - Aircraft decoder aggregation

---

## SDR Hardware

### `owrx/sdr.py`
**Type:** SDR source management
**Lines:** ~600
**Key Classes:**
- `SdrSource` - Base class for all SDR types
- `SdrSourceEventClient` - Event-driven SDR interface
- `SdrService` - SDR lifecycle service

**State Machine:**
```
STOPPED → STARTING → RUNNING → STOPPING → FAILED
```

### `owrx/source/` Directory (27 SDR Drivers)

**Consumer SDRs:**
- `rtlsdr.py` - RTL-SDR dongles
- `rtltcp.py` - RTL-SDR via rtl_tcp
- `sdrplay.py` - SDRplay RSP series
- `airspy.py` - Airspy R2/Mini
- `airspyhf.py` - Airspy HF+
- `hackrf.py` - HackRF One
- `fcdpp.py` - FunCube Dongle Pro+

**High-End SDRs:**
- `limesdr.py` - LimeSDR
- `pluto.py` - PlutoSDR
- `uhd.py` - Ettus USRP (via UHD)
- `bladerf.py` - BladeRF
- `perseus.py` - Perseus SDR

**Ham Radio SDRs:**
- `hpsdr.py` - HPSDR protocol devices
- `radioberry.py` - Radioberry
- `redpitaya.py` - Red Pitaya
- `rsp_tcp.py` - SDRplay via rsp_tcp
- `fifi_sdr.py` - FiFi-SDR
- `hydra.py` - HydraSDR

**Generic:**
- `soapy.py` - SoapySDR wrapper (supports many devices)
- `connector.py` - owrx-connector integration

Each driver implements:
- Hardware initialization
- Frequency/sample rate control
- Gain control (manual/AGC)
- PPM correction
- Device-specific parameters

### `owrx/soapy.py`
**Type:** SoapySDR integration
**Purpose:** Generic SDR hardware abstraction layer

---

## Property System

### `owrx/property/__init__.py`
**Type:** Reactive property system
**Key Classes:**
- `Property` - Observable value
- `PropertyManager` - Collection of properties
- `PropertyStack` - Layered properties
- `PropertyLayer` - Property overlay
- `PropertyCarousel` - Rotating values
- `PropertyReadOnly` - Read-only property wrapper

**Property Wiring:**
- `wire(callback)` - Subscribe to changes
- `unwire(callback)` - Unsubscribe

### `owrx/property/filter.py`
**Type:** Property transformations
**Classes:**
- `PropertyFilter` - Base filter
- `OrFilter` - Logical OR
- `AndFilter` - Logical AND
- `PropertyFilterChain` - Filter pipeline

### `owrx/property/validators.py`
**Type:** Value validation
**Validators:**
- `BoolValidator` - Boolean values
- `IntValidator` - Integer values with optional range
- `FloatValidator` - Float values with optional range
- `StringValidator` - String values
- `RegexValidator` - Regex pattern matching
- `NumberValidator` - Generic number validation
- `LambdaValidator` - Custom validation function

---

## Configuration

### `owrx/config/core.py`
**Type:** Core configuration
**Key Classes:**
- `CoreConfig` - Core settings (port, data dir, etc.)
- Configuration file parsing

### `owrx/config/defaults.py`
**Type:** Default values
**Purpose:** Default configuration for all settings

### `owrx/config/migration.py`
**Type:** Configuration migration
**Purpose:** Convert old Python config to new JSON config

### `owrx/config/dynamic.py`
**Type:** Dynamic configuration
**Purpose:** Runtime configuration updates

---

## Modes & Decoders

### `owrx/modes.py`
**Type:** Demodulation mode definitions
**Key Classes:**
- `Mode` - Base mode class
- `AnalogMode` - Analog modes (AM, FM, SSB, CW)
- `DigitalMode` - Digital modes (FT8, WSPR, DMR, etc.)

**Mode Registry:**
All available modes with their requirements, bandwidth, audio rates, etc.

### `owrx/wsjt.py`
**Type:** WSJT-X integration
**Purpose:** FT8, FT4, WSPR, JT65, JT9 decoding via wsjtx

### `owrx/js8.py`
**Type:** JS8Call integration
**Purpose:** JS8Call decoding

### `owrx/pocsag.py`
**Type:** POCSAG decoder
**Purpose:** Pager message decoding

### `owrx/fax.py`
**Type:** Weather fax decoder
**Purpose:** HF fax image decoding

### `owrx/sstv.py`
**Type:** SSTV decoder
**Purpose:** SSTV image decoding

---

## APRS & Position Reporting

### `owrx/aprs/__init__.py`
**Type:** APRS packet handling
**Purpose:** Parse and process APRS packets

### `owrx/aprs/kiss.py`
**Type:** KISS protocol
**Purpose:** KISS TNC protocol implementation

---

## Map & Visualization

### `owrx/map.py`
**Type:** Map functionality
**Purpose:** Map display, marker management

### `owrx/markers.py`
**Type:** Map markers
**Purpose:** Broadcast, repeater, aircraft markers

### `owrx/aircraft.py`
**Type:** Aircraft tracking
**Purpose:** ADSB aircraft position tracking

### `owrx/marine.py`
**Type:** Maritime data
**Purpose:** AIS ship tracking

### `owrx/icao.py`
**Type:** ICAO database
**Purpose:** Aircraft registration lookup

---

## Bookmarks & Bands

### `owrx/bookmarks.py`
**Type:** Bookmark management
**Lines:** ~400
**Key Classes:**
- `Bookmarks` - Bookmark collection
- `Bookmark` - Individual bookmark

**Sources:**
- Static JSON files (`bookmarks.d/`)
- EIBI shortwave broadcast database
- Repeater databases
- User bookmarks

### `owrx/bands.py`
**Type:** Band plan management
**Purpose:** Frequency band definitions (HF, VHF, UHF, etc.)

---

## Reporting & External Services

### `owrx/reporting/pskreporter.py`
**Type:** PSK Reporter integration
**Purpose:** Upload decoded signals to PSK Reporter

### `owrx/reporting/wsprnet.py`
**Type:** WSPRNet integration
**Purpose:** Upload WSPR spots to WSPRNet

### `owrx/reporting/mqtt.py`
**Type:** MQTT publishing
**Purpose:** Publish decoded data to MQTT broker

---

## Waterfall & FFT

### `owrx/fft.py`
**Type:** FFT processing
**Lines:** ~300
**Key Classes:**
- `FftProfile` - FFT profile (size, interval)
- `FftService` - FFT computation service

**FFT Types:**
- Standard FFT (waterfall)
- High-resolution FFT (spectrum analyzer)

### `owrx/waterfall.py`
**Type:** Waterfall visualization
**Purpose:** Waterfall color mapping, compression

---

## Audio Processing

### `owrx/audio/__init__.py`
**Type:** Audio utilities
**Purpose:** Audio format detection, conversion

### `owrx/audio/chopper.py`
**Type:** Audio segmentation
**Purpose:** Split audio into chunks for decoders

### `owrx/audio/queue.py`
**Type:** Audio queueing
**Purpose:** Audio buffer management

---

## User Management

### `owrx/users.py`
**Type:** User authentication
**Key Classes:**
- `User` - User account
- `UserList` - User collection
- Password hashing (bcrypt)

---

## Services

### `owrx/service/schedule.py`
**Type:** Scheduled tasks
**Purpose:** Cron-like task scheduling

### `owrx/service/chain.py`
**Type:** Service chains
**Purpose:** Service dependency management

---

## Utilities

### `owrx/version.py`
**Type:** Version management
**Purpose:** Application version string

### `owrx/metrics.py`
**Type:** Metrics collection
**Purpose:** Prometheus-compatible metrics

### `owrx/cpu.py`
**Type:** CPU monitoring
**Purpose:** CPU usage tracking

### `owrx/storage.py`
**Type:** Data storage
**Purpose:** File storage abstraction

### `owrx/lookup.py`
**Type:** Callsign lookup
**Purpose:** Ham radio callsign database lookup

### `owrx/color.py`
**Type:** Color themes
**Purpose:** Waterfall color scheme management

### `owrx/breadcrumb.py`
**Type:** Navigation
**Purpose:** Breadcrumb navigation for settings

### `owrx/command.py`
**Type:** Command execution
**Purpose:** External command execution utilities

### `owrx/rigcontrol.py`
**Type:** Rig control
**Purpose:** Hamlib rig control integration

### `owrx/receiverid.py`
**Type:** Receiver identification
**Purpose:** Unique receiver ID generation

### `owrx/feature.py`
**Type:** Feature detection
**Lines:** ~500
**Purpose:** Detect available external programs and capabilities

**Detection Methods:**
- Binary existence (`which`)
- Version checking
- Module imports
- Runtime testing

### `owrx/gps.py`
**Type:** GPS location
**Purpose:** Receiver location updates

---

## Form System

### `owrx/form/__init__.py`
**Type:** Form generation
**Purpose:** Dynamic form generation for settings

**Field Types:**
- Text, Number, Float
- Checkbox, Dropdown, Radio
- Color picker
- Location picker
- Multi-value fields

### `owrx/form/error.py`
**Type:** Form validation
**Purpose:** Form error handling

### `owrx/form/section.py`
**Type:** Form sections
**Purpose:** Grouped form fields

---

## Logging

### `owrx/log/__init__.py`
**Type:** Logging setup
**Purpose:** Structured logging configuration

---

## Frontend JavaScript (htdocs/lib/)

### Key UI Modules

- **`AudioEngine.js`** - Web Audio API wrapper, audio decoding/playback
- **`Demodulator.js`** - Demodulator control, frequency management
- **`Waterfall.js`** - Canvas-based waterfall display
- **`Spectrum.js`** - Spectrum analyzer display
- **`FrequencyDisplay.js`** - Frequency readout
- **`BookmarkBar.js`** - Bookmark UI
- **`MapManager.js`** - Map display (Leaflet/Google Maps)
- **`MapMarkers.js`** - Map marker management
- **`MessagePanel.js`** - Decoded message display
- **`Scanner.js`** - Frequency scanner
- **`Chat.js`** - User chat
- **`Shortcuts.js`** - Keyboard shortcuts
- **`ProgressBar.js`** - Progress indicator
- **`Nanoq.js`** - Promise-based utilities

---

## Testing

### `test/` Directory
**Framework:** Python unittest
**Coverage:** Property system (21 test modules)

**Test Categories:**
- Property validation
- Property filters
- Property layers and stacks
- Property deletion/readonly behavior

**Run Tests:**
```bash
python3 -m pytest test/
```

---

## Build System

### `buildall.sh`
**Type:** Build script
**Purpose:** Build all OpenWebRX+ dependencies from source

**Builds:**
- csdr (DSP library)
- pycsdr (Python bindings)
- owrx-connector (SDR connectors)
- codecserver (codec server)
- digiham (digital voice decoders)
- js8py (JS8Call integration)
- redsea (RDS decoder)
- dablin (DAB decoder)

### `docker.sh`
**Type:** Docker builder
**Purpose:** Build Docker images for various architectures

---

## Module Dependencies

**Critical Dependencies:**
- `pycsdr` >= 0.18.36 (DSP processing)
- `owrx-connector` >= 0.6.5 (SDR hardware)
- Python 3.5+

**Optional Dependencies:**
- `digiham` (DMR, YSF, D-Star, NXDN)
- `js8py` (JS8Call)
- `paho-mqtt` (MQTT reporting)
- `csdr-eti` (DAB support)

**External Programs:**
- `wsjtx`, `js8call`, `direwolf`, `dream-headless`
- `dump1090-fa`, `dumpvdl2`, `dumphfdl`, `acarsdec`
- `rtl-433`, `multimon-ng`, `redsea`, `dablin`, `nrsc5`
- `lame` (MP3 encoding)
- `imagemagick` (image processing)
