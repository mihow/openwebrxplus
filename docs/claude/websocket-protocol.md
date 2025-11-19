# OpenWebRX+ WebSocket Protocol

## Overview

OpenWebRX+ uses WebSockets for real-time bidirectional communication between the server and web clients. The protocol handles both text (JSON) and binary (audio/FFT) messages.

**Implementation:** Custom WebSocket implementation (not using external libraries)
**Location:** `owrx/websocket.py`, `owrx/connection.py`

## Connection Lifecycle

### 1. Connection Establishment

```
HTTP GET /ws/
    ↓
Upgrade header detected
    ↓
WebSocket handshake (101 Switching Protocols)
    ↓
WebSocket connection established
    ↓
OpenWebRxReceiverClient created
    ↓
Initial configuration sent to client
    ↓
Client ready for audio/FFT streaming
```

**HTTP Headers:**
```
GET /ws/ HTTP/1.1
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <random-key>
Sec-WebSocket-Version: 13
```

**Server Response:**
```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: <hashed-key>
```

### 2. Active Connection

Client receives:
- Binary audio frames (compressed audio)
- Binary FFT data (waterfall)
- JSON metadata (decoded messages, config updates)
- JSON status updates (S-meter, frequency, etc.)

Client sends:
- JSON control messages (frequency changes, mode changes)
- JSON chat messages
- JSON configuration requests

### 3. Connection Termination

```
User closes browser tab
    ↓
WebSocket close frame sent
    ↓
Server receives close
    ↓
OpenWebRxReceiverClient.close() called
    ↓
DSP chain stopped
    ↓
Client removed from active list
    ↓
Resources cleaned up
```

## Message Types

### Server → Client Messages

#### 1. Audio Frames (Binary)

**Format:** Raw binary audio data (compressed)
**Encoding:** Opus or ADPCM (configurable)
**Frame Rate:** ~20-50 frames/second
**Frame Size:** Variable (typically 100-500 bytes)

**Message Structure:**
```
[Audio sample bytes...]
```

No header, just raw compressed audio samples.

#### 2. FFT Data (Binary)

**Format:** Compressed FFT spectrum data for waterfall
**Compression:** Custom compression (zlib optional)
**Update Rate:** 5-30 FPS (configurable)

**Message Structure:**
```
[FFT bin values...]
```

Each value represents power at a frequency bin.

#### 3. Configuration (JSON)

Initial configuration sent on connection.

```json
{
    "type": "config",
    "value": {
        "receiver_name": "OpenWebRX+",
        "receiver_location": "Grid Square",
        "center_freq": 7074000,
        "sdr_id": "rtlsdr-0",
        "profile_id": "ft8",
        "start_freq": 7074000,
        "start_mod": "usb",
        "waterfall_min": -88,
        "waterfall_max": -20,
        "waterfall_colors": "default",
        "fft_size": 4096,
        "audio_rate": 12000,
        "fft_fps": 10,
        "max_clients": 20,
        "features": ["digital_voice", "wsjt", "packet"]
    }
}
```

#### 4. Receiver Information (JSON)

Receiver details and capabilities.

```json
{
    "type": "receiver_details",
    "value": {
        "receiver_name": "OpenWebRX+",
        "receiver_location": "Grid Square",
        "receiver_gps": {"lat": 40.7128, "lon": -74.0060},
        "photo": "/static/photo.jpg",
        "antenna": "Dipole",
        "receiver_admin": "callsign"
    }
}
```

#### 5. Profiles (JSON)

Available demodulation profiles.

```json
{
    "type": "profiles",
    "value": [
        {
            "id": "ft8",
            "name": "FT8",
            "center_freq": 7074000,
            "modulation": "usb"
        },
        {
            "id": "aprs",
            "name": "APRS",
            "center_freq": 144390000,
            "modulation": "nfm"
        }
    ]
}
```

#### 6. Features (JSON)

Available features based on installed decoders.

```json
{
    "type": "features",
    "value": {
        "digital_voice": ["dmr", "ysf", "dstar", "nxdn"],
        "wsjt": ["ft8", "ft4", "wspr", "jt65", "jt9"],
        "packet": ["aprs"],
        "pocsag": true,
        "sstv": true,
        "fax": true
    }
}
```

#### 7. S-Meter (JSON)

Signal strength meter readings.

```json
{
    "type": "smeter",
    "value": -73.5
}
```

Sent periodically (every 100-500ms).

#### 8. Metadata (JSON)

Decoded messages from digital modes.

```json
{
    "type": "ft8_message",
    "value": {
        "timestamp": 1234567890,
        "db": -12,
        "dt": 0.3,
        "freq": 1234,
        "message": "CQ DX K1ABC FN42",
        "callsign": "K1ABC",
        "locator": "FN42"
    }
}
```

**Message Types:**
- `ft8_message`, `ft4_message`, `wspr_message`
- `aprs_message`
- `pocsag_message`
- `sstv_image`
- `fax_image`
- `dmr_message`, `ysf_message`, `dstar_message`
- `js8_message`

#### 9. Frequency Updates (JSON)

Dial frequency updates (for multi-mode operation).

```json
{
    "type": "dial_frequencies",
    "value": {
        "ft8": 7074000,
        "wspr": 7038600,
        "aprs": 144390000
    }
}
```

#### 10. Bookmarks (JSON)

Frequency bookmarks.

```json
{
    "type": "bookmarks",
    "value": [
        {
            "name": "WWV 10 MHz",
            "frequency": 10000000,
            "modulation": "am"
        },
        {
            "name": "FT8 40m",
            "frequency": 7074000,
            "modulation": "usb"
        }
    ]
}
```

#### 11. Map Markers (JSON)

Map markers (stations, aircraft, ships).

```json
{
    "type": "aprs_data",
    "value": {
        "callsign": "K1ABC-9",
        "lat": 40.7128,
        "lon": -74.0060,
        "course": 90,
        "speed": 55,
        "altitude": 100,
        "symbol": "car",
        "comment": "Mobile station"
    }
}
```

#### 12. Chat Messages (JSON)

User chat messages.

```json
{
    "type": "chat",
    "value": {
        "user": "K1ABC",
        "message": "Hello from New York!",
        "timestamp": 1234567890
    }
}
```

#### 13. Client Count (JSON)

Number of connected clients.

```json
{
    "type": "clients",
    "value": 5
}
```

#### 14. Background Decoder Status (JSON)

Status of background decoders (APRS, POCSAG, etc.).

```json
{
    "type": "secondary_demod",
    "value": {
        "aprs": "running",
        "pocsag": "running",
        "adsb": "stopped"
    }
}
```

### Client → Server Messages

All client messages are JSON.

#### 1. DSP Control

Change DSP parameters (frequency, mode, etc.).

```json
{
    "type": "dspcontrol",
    "params": {
        "frequency": 7074000,
        "mod": "usb",
        "low_cut": 300,
        "high_cut": 3000,
        "offset_freq": 1500,
        "squelch_level": -150
    }
}
```

**Parameters:**
- `frequency` - Tuned frequency (Hz)
- `mod` - Modulation mode (am, fm, usb, lsb, etc.)
- `low_cut` - Low-pass filter cutoff (Hz)
- `high_cut` - High-pass filter cutoff (Hz)
- `offset_freq` - Demodulator offset (Hz)
- `squelch_level` - Squelch threshold (dB)

#### 2. Audio Start/Stop

Start or stop audio streaming.

```json
{"type": "audiostart"}
```

```json
{"type": "audiostop"}
```

#### 3. Connection Properties

Client capabilities and preferences.

```json
{
    "type": "connectionproperties",
    "params": {
        "audio_compression": "opus",
        "fft_compression": "zlib",
        "sdr_id": "rtlsdr-0",
        "profile_id": "ft8"
    }
}
```

#### 4. Chat Message

Send chat message to all users.

```json
{
    "type": "chat",
    "message": "Hello everyone!"
}
```

#### 5. Configuration Request

Request current configuration.

```json
{"type": "config"}
```

Server responds with `config` message.

## Binary Message Formats

### Audio Frame Format

OpenWebRX+ supports multiple audio compression formats:

**1. Opus (Preferred)**
- Best quality/compression ratio
- Variable bitrate
- ~12-32 kbps typical

**2. ADPCM**
- Lower CPU usage
- Fixed bitrate
- ~32-64 kbps typical

**Frame Structure:**
```
[Compressed audio bytes]
```

No wrapper, just raw codec output.

### FFT Frame Format

**Uncompressed:**
```
[int8_t bin0, int8_t bin1, ..., int8_t binN]
```

Each bin is a signed 8-bit value representing dB power.

**Compressed (optional):**
```
[zlib compressed FFT data]
```

## Connection Flow Examples

### Example 1: Initial Connection

```
1. Client: HTTP GET /ws/
2. Server: 101 Switching Protocols
3. Server → Client: {"type": "config", "value": {...}}
4. Server → Client: {"type": "receiver_details", "value": {...}}
5. Server → Client: {"type": "profiles", "value": [...]}
6. Server → Client: {"type": "features", "value": {...}}
7. Server → Client: {"type": "bookmarks", "value": [...]}
8. Client → Server: {"type": "connectionproperties", "params": {...}}
9. Client → Server: {"type": "audiostart"}
10. Server → Client: [Binary audio frames start streaming]
11. Server → Client: [Binary FFT frames start streaming]
12. Server → Client: {"type": "smeter", "value": -73.5} (periodic)
```

### Example 2: Tuning to New Frequency

```
1. User clicks on waterfall at 7074000 Hz
2. Client calculates new frequency
3. Client → Server: {"type": "dspcontrol", "params": {"frequency": 7074000}}
4. Server updates DSP chain
5. Server retunes SDR (if necessary)
6. Server → Client: [New audio for new frequency]
7. Server → Client: {"type": "smeter", "value": -65.2}
```

### Example 3: Changing Mode

```
1. User selects "FT8" mode
2. Client → Server: {"type": "dspcontrol", "params": {"mod": "usb", "low_cut": 300, "high_cut": 3000}}
3. Server switches demodulator chain
4. Server starts FT8 decoder
5. Server → Client: [Audio in new mode]
6. (30 seconds later)
7. Server → Client: {"type": "ft8_message", "value": {...}} (decoded FT8)
```

### Example 4: Background APRS Decoding

```
1. User enables APRS on map
2. Client → Server: {"type": "secondary_demod", "params": {"aprs": "start"}}
3. Server starts APRS decoder chain
4. Server starts direwolf process
5. (When packet received)
6. Server → Client: {"type": "aprs_data", "value": {...}}
7. Client adds marker to map
```

## WebSocket Message Handling (Code)

### Server-Side Handler

```python
# owrx/websocket.py
class WebSocketConnection:
    def handle_message(self, message):
        if isinstance(message, bytes):
            # Binary message (not expected from client)
            pass
        else:
            # JSON text message
            parsed = json.loads(message)
            msg_type = parsed.get("type")

            if msg_type == "dspcontrol":
                self.handle_dsp_control(parsed["params"])
            elif msg_type == "audiostart":
                self.start_audio()
            elif msg_type == "audiostop":
                self.stop_audio()
            elif msg_type == "chat":
                self.handle_chat(parsed["message"])
            # ... etc

    def send_audio(self, audio_bytes):
        # Send binary audio frame
        self.send_message(audio_bytes, binary=True)

    def send_metadata(self, msg_type, data):
        # Send JSON message
        self.send_message(json.dumps({
            "type": msg_type,
            "value": data
        }))
```

### Client-Side Handler

```javascript
// htdocs/lib/AudioEngine.js
class AudioEngine {
    constructor() {
        this.ws = new WebSocket("ws://" + window.location.host + "/ws/");
        this.ws.binaryType = "arraybuffer";

        this.ws.onmessage = (event) => {
            if (event.data instanceof ArrayBuffer) {
                // Binary message (audio or FFT)
                this.handleBinaryMessage(event.data);
            } else {
                // JSON text message
                const msg = JSON.parse(event.data);
                this.handleJsonMessage(msg);
            }
        };
    }

    handleBinaryMessage(data) {
        // Decode and play audio
        this.audioDecoder.decode(data);
    }

    handleJsonMessage(msg) {
        switch (msg.type) {
            case "config":
                this.applyConfig(msg.value);
                break;
            case "smeter":
                this.updateSMeter(msg.value);
                break;
            case "ft8_message":
                this.displayFt8Message(msg.value);
                break;
            // ... etc
        }
    }

    setFrequency(freq) {
        this.ws.send(JSON.stringify({
            type: "dspcontrol",
            params: {frequency: freq}
        }));
    }
}
```

## Performance Considerations

### Bandwidth Usage

**Typical bandwidth per client:**
- Audio: 12-64 kbps (depends on compression)
- FFT: 5-50 kbps (depends on resolution and FPS)
- Metadata: 0.1-5 kbps (depends on mode)
- **Total: ~20-120 kbps per client**

**Optimization Strategies:**
- Reduce FFT frame rate for slower connections
- Use Opus compression for audio (better than ADPCM)
- Compress FFT data (zlib)
- Limit max clients
- Bandwidth throttling per client

### CPU Usage

**Server-Side:**
- FFT computation (shared across clients)
- Audio compression per client
- Decoder processes (wsjtx, direwolf, etc.)

**Client-Side:**
- Audio decompression (Opus/ADPCM)
- Canvas rendering (waterfall)
- FFT visualization

### Latency

**Typical latencies:**
- Audio: 100-500ms (buffering + compression + network)
- FFT: 50-200ms
- Metadata: 0-50ms

**Factors:**
- Network RTT
- Audio buffer size
- FFT frame rate
- Server load

## Error Handling

### Connection Errors

**Client reconnection:**
```javascript
ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    // Attempt reconnection after 5 seconds
    setTimeout(() => {
        this.connect();
    }, 5000);
};
```

**Server error handling:**
```python
try:
    self.send_message(data)
except Exception as e:
    logger.error(f"Error sending message: {e}")
    self.close()
```

### Message Validation

**Server-side:**
```python
def handle_dsp_control(self, params):
    if "frequency" in params:
        freq = params["frequency"]
        if not (0 <= freq <= 6000000000):  # 6 GHz max
            logger.warning(f"Invalid frequency: {freq}")
            return
        self.set_frequency(freq)
```

**Client-side:**
```javascript
if (msg.type === "config" && msg.value) {
    if (!msg.value.center_freq) {
        console.error("Invalid config: missing center_freq");
        return;
    }
    this.applyConfig(msg.value);
}
```

## Security Considerations

### Authentication

WebSocket connections inherit HTTP session authentication:
```python
if not self.is_authenticated():
    self.send_error("Authentication required")
    self.close()
    return
```

### Rate Limiting

Prevent abuse by limiting message rate:
```python
class RateLimiter:
    def __init__(self, max_per_second=10):
        self.max_per_second = max_per_second
        self.timestamps = []

    def allow(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 1]
        if len(self.timestamps) >= self.max_per_second:
            return False
        self.timestamps.append(now)
        return True

# In message handler
if not self.rate_limiter.allow():
    logger.warning("Rate limit exceeded")
    return
```

### Input Validation

Always validate client input:
```python
def handle_dsp_control(self, params):
    # Validate all parameters
    if "frequency" in params:
        if not isinstance(params["frequency"], (int, float)):
            return
    if "mod" in params:
        if params["mod"] not in VALID_MODES:
            return
```

## Debugging WebSocket Connections

### Server-Side Logging

```python
import logging
logging.getLogger("owrx.websocket").setLevel(logging.DEBUG)
```

### Client-Side Debugging

```javascript
// Log all messages
ws.onmessage = (event) => {
    console.log("Received:", event.data);
    // ... handle message
};

// Monitor connection state
ws.onopen = () => console.log("WebSocket connected");
ws.onclose = () => console.log("WebSocket disconnected");
ws.onerror = (e) => console.error("WebSocket error:", e);
```

### Browser DevTools

- **Network tab:** View WebSocket frames
- **Console:** Log messages
- **Performance:** Monitor CPU/memory usage
