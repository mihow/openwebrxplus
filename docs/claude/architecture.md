# OpenWebRX+ Architecture

## Overview

OpenWebRX+ follows a **modified MVC architecture** with real-time WebSocket communication and a reactive property system. The application manages SDR hardware, processes radio signals, and streams the results to multiple concurrent web clients.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browsers (Clients)                   │
│              (HTML5 Canvas, Web Audio API, WebSockets)           │
└────────────┬────────────────────────────────────────────────────┘
             │ WebSocket (Binary: Audio/FFT, JSON: Metadata)
             │ HTTP (Static Assets, API, Settings)
┌────────────┴────────────────────────────────────────────────────┐
│                   Python HTTP/WebSocket Server                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  HTTP Router (owrx/http.py)                             │   │
│  │  - Static Assets (owrx/controllers/assets.py)           │   │
│  │  - API Endpoints (owrx/controllers/api.py)              │   │
│  │  - Settings UI (owrx/controllers/settings/)             │   │
│  │  - WebSocket Handler (owrx/controllers/websocket.py)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Connection Manager (owrx/connection.py)                │   │
│  │  - Client Session Management                            │   │
│  │  - DSP Chain per Client                                 │   │
│  │  - Waterfall/Audio Streaming                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DSP Processing (owrx/dsp.py)                           │   │
│  │  - Demodulator Chains (csdr/chain/)                     │   │
│  │  - FFT Processing (owrx/fft.py)                         │   │
│  │  - Waterfall Generation (owrx/waterfall.py)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SDR Source Manager (owrx/sdr.py)                       │   │
│  │  - Hardware Abstraction                                 │   │
│  │  - Multi-SDR Support                                    │   │
│  │  - Frequency/Sample Rate Control                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Property System (owrx/property/)                       │   │
│  │  - Reactive Data Flow                                   │   │
│  │  - Configuration Management                             │   │
│  │  - Property Wiring/Change Propagation                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────────────┐
│                    SDR Hardware Layer                            │
│  - owrx-connector (native binary connectors)                    │
│  - SoapySDR (hardware abstraction)                              │
│  - Driver libraries (rtl-sdr, hackrf, etc.)                     │
└────────────┬────────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────────────┐
│                    Physical SDR Hardware                         │
│  RTL-SDR, HackRF, SDRplay, Airspy, LimeSDR, etc.                │
└─────────────────────────────────────────────────────────────────┘
```

## Core Subsystems

### 1. HTTP Server & Routing

**Location:** `owrx/__main__.py`, `owrx/http.py`

The application uses Python's built-in `http.server.HTTPServer` with a custom request handler (`RequestHandler` in http.py). The router supports:
- Static routes (exact path matches)
- Regex routes (pattern-based matching)
- Method-based routing (GET, POST, DELETE, etc.)
- Controller instantiation per request

**Request Flow:**
1. HTTP request arrives
2. Router matches path to controller
3. Controller instantiated with request context
4. Controller processes request
5. Response sent (HTML, JSON, binary, or WebSocket upgrade)

### 2. WebSocket Communication

**Location:** `owrx/websocket.py`, `owrx/connection.py`

OpenWebRX+ implements a custom WebSocket protocol (not using external libraries). Supports:
- Binary messages (audio samples, FFT data)
- Text messages (JSON metadata, status updates)
- Multiple simultaneous clients
- Per-client DSP chains

**Message Types:**
- `audio` - Compressed audio samples
- `fft` - Waterfall FFT data
- `hd_audio` - High-definition audio
- `smeter` - S-meter readings
- `metadata` - Decoder output (callsigns, text, etc.)
- `dial_frequencies` - Active frequency list
- `profiles` - Available demodulation profiles
- `features` - Available features
- `config` - Configuration updates

### 3. Property System

**Location:** `owrx/property/`

A reactive property management system inspired by functional reactive programming:

**Core Concepts:**
- **Property:** Observable value with change notification
- **PropertyStack:** Layered properties (base + overrides)
- **PropertyLayer:** Property overlay (for profiles, user settings)
- **PropertyCarousel:** Rotating property values
- **PropertyFilter:** Transformation pipeline
- **PropertyValidator:** Value validation

**Property Wiring:**
Properties can be wired together so changes propagate automatically.

**Example:**
```python
props = PropertyLayer()
props["frequency"] = 7074000

def on_freq_change(new_freq):
    print(f"Tuned to {new_freq}")

props.wire(on_freq_change)  # Subscribe to changes
props["frequency"] = 14074000  # Triggers callback
```

**Use Cases:**
- Configuration management
- SDR parameter changes
- Profile switching
- User preference layers

### 4. SDR Source Management

**Location:** `owrx/sdr.py`, `owrx/source/`

**Key Classes:**
- `SdrSource` - Base class for all SDR types
- `SdrSourceEventClient` - Event-driven SDR client
- `SdrClientClass` - Client factory
- `SdrService` - SDR lifecycle management

**SDR Driver Inheritance:**
```
SdrSource (base)
├── RtlSdrSource
├── SdrplaySource
├── HackrfSource
├── AirspySource
├── LimeSDRSource
└── SoapyConnectorSource (generic SoapySDR wrapper)
    ├── RedPitayaSource
    ├── RadioberrySource
    └── ... (other SoapySDR devices)
```

**Responsibilities:**
- Hardware detection and initialization
- Sample rate and frequency control
- Gain control (manual/AGC)
- PPM correction
- Multi-profile support (shared SDR among multiple uses)
- State management (starting, running, stopping, failed)

### 5. DSP Processing Pipeline

**Location:** `owrx/dsp.py`, `csdr/chain/`, `csdr/module/`

**Signal Flow:**
```
SDR Hardware → Source Connector → Selector (frequency/bandwidth) →
Demodulator Chain → Audio Processing → Compression → Client WebSocket
```

**Key Classes:**
- `DspManager` - Manages DSP chains for a receiver
- `CsdrDspChain` - Base DSP processing chain
- `Demodulator` - Specific demodulation chain (AM, FM, FT8, etc.)
- `SecondaryDemodulator` - Background decoders (APRS, POCSAG, etc.)

**Demodulator Types:**
- Analog: `AnalogDemodulatorChain` (AM, FM, SSB, CW)
- Digital Voice: `DigitalVoiceDemodulatorChain` (DMR, YSF, D-Star)
- Digital Data: `Hd/Wsjt/Ft8/Packet/...DemodulatorChain`
- FFT: `FftChain` (for waterfall)

**Processing Pipeline Construction:**
Chains are dynamically constructed based on:
- Selected mode
- Available features (external decoders)
- Audio format requirements
- Client capabilities

### 6. Feature Detection

**Location:** `owrx/feature.py`

Runtime detection of external programs and libraries:

**Detection Methods:**
- Binary existence check (`which <program>`)
- Version checking
- Capability testing
- Python module imports

**Feature Categories:**
- Digital mode decoders (wsjtx, js8call, direwolf)
- Audio codecs (codec2, freedv)
- Image decoders (multimon-ng for fax/sstv)
- Aviation decoders (dump1090, dumpvdl2, dumphfdl)
- Other utilities (lame, imagemagick)

**Impact:**
Missing features automatically disable corresponding modes in the UI.

### 7. Background Services

**Location:** `owrx/service/`

Long-running background tasks:
- **Scheduled Services:** Periodic tasks (cleanup, updates)
- **Decoder Services:** Continuous decoding (APRS, ADSB, etc.)
- **Profile Services:** Per-profile SDR configurations

**Service Lifecycle:**
1. Service definition in configuration
2. Service manager instantiation
3. Automatic start/stop based on conditions
4. Resource cleanup on shutdown

### 8. Configuration System

**Location:** `owrx/config/`

**Two-tier Configuration:**
1. **Core Config** (`openwebrx.conf`) - Server settings, data dir, ports
2. **Web Config** (stored in data directory) - Receiver settings, SDRs, profiles

**Configuration Migration:**
Automatic migration from old Python config files to new JSON-based web config.

**Configuration Hierarchy:**
```
Core Defaults → User Config → Profile Layer → Session Overrides
```

### 9. Frontend Architecture

**Location:** `htdocs/`

**Technology Stack:**
- HTML5 (Canvas, Web Audio API, WebSockets)
- JavaScript (ES5/ES6)
- jQuery 3.2.1
- Bootstrap 4

**Key JavaScript Modules:**
- `Demodulator.js` - Demodulation control and frequency management
- `AudioEngine.js` - Web Audio API wrapper, audio routing
- `Waterfall.js` - Canvas-based waterfall display
- `Spectrum.js` - Spectrum analyzer display
- `BookmarkBar.js` - Bookmark UI
- `MessagePanel.js` - Decoded message display
- `MapManager.js` - Map integration (Leaflet/Google Maps)
- `Scanner.js` - Frequency scanning

**Frontend-Backend Communication:**
- Initial page load: HTTP GET for HTML
- Asset loading: HTTP GET for JS/CSS/images
- WebSocket connection for real-time data
- AJAX for configuration changes

## Data Flow Examples

### Example 1: Tuning to a New Frequency

```
User clicks on waterfall
    ↓
JavaScript updates frequency in Demodulator.js
    ↓
WebSocket message sent to server: {type: "dspcontrol", params: {frequency: 7074000}}
    ↓
Server (owrx/connection.py) receives message
    ↓
DSP chain updated (owrx/dsp.py)
    ↓
SDR source tuned (if necessary)
    ↓
New audio/metadata flows through DSP chain
    ↓
Compressed audio sent to client via WebSocket
    ↓
Client AudioEngine decodes and plays audio
```

### Example 2: Background APRS Decoding

```
SDR receives 144.390 MHz (APRS frequency)
    ↓
Source connector streams IQ samples
    ↓
Secondary demodulator chain (APRS) receives samples
    ↓
Direwolf decoder processes audio
    ↓
APRS packets extracted
    ↓
owrx/aprs.py parses packets
    ↓
Packets stored and sent to map display
    ↓
WebSocket message to all clients: {type: "aprs", data: {...}}
    ↓
Client MapManager updates map markers
```

## Concurrency Model

**Threading:**
- Main thread: HTTP server
- Per-client threads: WebSocket connections
- Worker threads: DSP processing
- Background threads: Services, decoders

**Process Model:**
- Main Python process
- External decoder processes (wsjtx, direwolf, etc.)
- owrx-connector processes (SDR hardware access)

**IPC Mechanisms:**
- Pipes: Communication with external decoders
- WebSockets: Client communication
- File descriptors: Audio/IQ sample streaming

## Scalability Considerations

**Multi-User Support:**
- Shared SDR across multiple users
- Per-user DSP chains
- Bandwidth limitation per client
- Maximum client limits

**Resource Management:**
- CPU usage monitoring
- Automatic service shutdown on high load
- Client disconnection on resource exhaustion

## Security Model

**Authentication:**
- Optional user authentication (login required)
- Session management
- Password hashing

**Authorization:**
- Admin vs. regular user roles
- IP-based banning
- Rate limiting

**Data Protection:**
- Optional HTTPS/TLS
- Secure WebSocket (WSS)
- No sensitive data exposure in logs

## Extension Architecture

**Plugin Points:**
1. New SDR drivers: Inherit from `SdrSource`
2. New demodulators: Inherit from appropriate chain base class
3. New controllers: Add to router in `owrx/http.py`
4. New UI components: Add JavaScript module to `htdocs/lib/`
5. New services: Implement service interface
6. New configuration sections: Add to `owrx/form/`

## Performance Characteristics

**Bottlenecks:**
- FFT computation (CPU-intensive)
- Audio compression (CPU-intensive)
- WebSocket throughput (network-limited)
- SDR hardware sample rate (hardware-limited)

**Optimizations:**
- Shared FFT across clients
- Audio compression (opus, adpcm)
- Waterfall frame rate limiting
- Selective feature enablement

## Error Handling

**Strategy:**
- Graceful degradation (disable features if decoders unavailable)
- Client-specific error isolation (one client crash doesn't affect others)
- Automatic service restart on failure
- Detailed logging for debugging

**Error Recovery:**
- SDR reconnection on hardware failure
- Service restart on decoder crash
- Client reconnection on WebSocket drop
