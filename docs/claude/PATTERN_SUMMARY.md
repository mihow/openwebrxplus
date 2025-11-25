# OpenWebRX+ LoRa Implementation Pattern Summary

## 1. MODE DEFINITION PATTERN (owrx/modes.py)

### How Modes Are Registered
Modes are defined as instances in a class variable `Modes.mappings` list:

```python
class Modes(object):
    mappings = [
        # Analog modes
        AnalogMode("nfm", "FM", bandpass=Bandpass(-4000, 4000)),
        
        # Digital modes with underlying modulation
        DigitalMode("packet", "Packet", underlying=["empty"]),
        
        # Service-only modes (background decoding)
        ServiceOnlyMode("noaa-apt-15", "NOAA-15 APT", 
                       underlying=["empty"],
                       requirements=["wxsat"]),
    ]
```

### Key Mode Classes

**AnalogMode**
- Basic modes without external decoders
- Examples: FM, AM, USB, LSB

**DigitalMode**
- Wraps external decoders with an underlying modulation
- Has parent class method `get_underlying_mode()` for bandpass
- Supports secondary FFT display
- Can specify custom bandpass or inherit from underlying

**ServiceOnlyMode(DigitalMode)**
- Background-only modes (not user-selectable in UI)
- For services like recording, weather satellite reception
- `service=True` flag prevents client-side selection

### Mode Registration for LoRa

```python
# In modes.py Modes.mappings list
ServiceOnlyMode(
    "lora",
    "LoRa",
    underlying=["empty"],
    bandpass=None,
    ifRate=250000,  # Fixed sample rate for lorarx
    requirements=["lora"],
    service=True,
    squelch=False
)
```

### Key Attributes

- **modulation** - Unique identifier (used in factory/dsp.py)
- **name** - Display name in UI
- **bandpass** - Frequency filter (Bandpass object or None)
- **ifRate** - Fixed IF sample rate (if mode requires specific rate)
- **requirements** - List of feature names to check availability
- **service** - Only available as background service (True/False)
- **squelch** - Whether squelch is applicable (True/False)

---

## 2. FEATURE DETECTION PATTERN (owrx/feature.py)

### How Feature Detection Works

```python
class FeatureDetector(object):
    features = {
        "lora": ["lorarx"],           # Feature → List of required binaries
        "ism": ["rtl_433"],
        "adsb": ["dump1090"],
        "digital_voice_digiham": ["digiham", "codecserver_ambe"],
    }
```

### Detection Mechanism

1. **Feature Registry** - Static dict mapping feature name → list of requirements
2. **Requirement Methods** - Dynamic dispatch pattern using `has_<requirement>()` methods
3. **Caching** - 2-hour cache to avoid repeated shell calls

```python
def has_requirement(self, requirement):
    cache = FeatureCache.getSharedInstance()
    if cache.has(requirement):
        return cache.get(requirement)
    
    method = self._get_requirement_method(requirement)
    result = False
    if method is not None:
        result = method()
    else:
        logger.error("detection of requirement {0} not implemented")
    
    cache.set(requirement, result)
    return result

def _get_requirement_method(self, requirement):
    methodname = "has_" + requirement
    if hasattr(self, methodname) and callable(getattr(self, methodname)):
        return getattr(self, methodname)
    return None
```

### Requirement Methods Pattern

```python
def has_lorarx(self):
    """
    OpenWebRX uses the lorarx LoRa decoder to decode LoRa signals.
    You can download and install it from http://oe5dxl.hamspirit.at:8025/aprs/bin/
    """
    return self.command_is_runnable("lorarx --help")

def has_rtl_433(self):
    """RTL-433 is required for ISM signal decoding"""
    return self.command_is_runnable("rtl_433 -h")
```

### Availability Check

```python
def is_available(self):
    fd = FeatureDetector()
    return reduce(lambda a, b: a and b, 
                  [fd.is_available(r) for r in self.requirements], 
                  True)
```

### LoRa Feature Detection

```python
# In FeatureDetector.features dict
"lora": ["lorarx"],

# Add requirement method
def has_lorarx(self):
    """
    OpenWebRX uses lorarx to decode LoRa signals. 
    Install from: http://oe5dxl.hamspirit.at:8025/aprs/bin/lorarx
    """
    return self.command_is_runnable("lorarx --help")
```

---

## 3. PARSER PATTERN (owrx/toolbox.py)

### Base Parser Classes

```python
class TextParser(LineBasedModule, DataRecorder):
    """Base for text-output decoders"""
    
    def __init__(self, filePrefix: str = None, service: bool = False):
        self.service = service
        DataRecorder.__init__(self, filePrefix, ".txt")
        LineBasedModule.__init__(self)
    
    def myName(self):
        return "%s%s%s" % (
            "Service" if self.service else "Client",
            " " + self.filePfx if self.filePfx else "",
            " at %dkHz" % (self.frequency // 1000) if self.frequency > 0 else ""
        )
    
    def parse(self, msg: bytes):
        """Override to parse decoder output - return JSON dict or None"""
        return None
    
    def process(self, line: bytes) -> any:
        """Called for each line from decoder. Handles file recording."""
        try:
            out = self.parse(line)
            if self.service and self.filePfx is not None:
                if out:
                    self.writeFile(str(out).encode("utf-8") + b"\n")
                elif out is None and len(line) > 0:
                    self.writeFile(line + b"\n")
        except Exception as exptn:
            logger.error("%s: Exception parsing: %s" % (self.myName(), str(exptn)))
        
        return out if out and not self.service else None
```

### Parser Implementation Pattern

```python
class IsmParser(TextParser):
    def __init__(self, service: bool = False):
        self.colors = ColorCache()
        super().__init__(filePrefix="ISM", service=service)
    
    def parse(self, msg: bytes):
        # 1. Parse JSON from decoder output
        out = json.loads(msg)
        
        # 2. Add mode name
        out["mode"] = "ISM"
        
        # 3. Convert timestamps if needed
        if "time" in out:
            out["timestamp"] = int(out["time"]) * 1000
            del out["time"]
        
        # 4. Add frequency (set by demodulator chain)
        if self.frequency:
            out["freq"] = self.frequency
        
        # 5. Report to external services (APRS-IS, MQTT, etc)
        ReportingEngine.getSharedInstance().spot(out)
        
        # 6. Color-code in interactive mode
        if not self.service:
            out["color"] = self.colors.getColor(out["id"])
        
        # 7. Return JSON for WebSocket transport
        return out
```

### LoRa Parser Implementation

```python
class LoRaParser(TextParser):
    def __init__(self, service: bool = False):
        self.colors = ColorCache()
        super().__init__(filePrefix="LoRa", service=service)
    
    def parse(self, msg: bytes):
        out = json.loads(msg)
        out["mode"] = "LoRa"
        
        # Convert Unix timestamps to milliseconds
        if "time" in out:
            out["timestamp"] = int(out["time"]) * 1000
            del out["time"]
        
        # Add center frequency if known
        if self.frequency:
            out["freq"] = self.frequency
        
        # Report to external services
        ReportingEngine.getSharedInstance().spot(out)
        
        # Color by sender ID in interactive mode
        if not self.service and "from" in out:
            out["color"] = self.colors.getColor(out["from"])
        
        return out
```

### Key Parser Methods

- **parse(msg: bytes) → dict|None** - Parse one line, return JSON dict or None
- **setDialFrequency(frequency: int)** - Called when tuning frequency changes
- **writeFile(data: bytes)** - Write to log file (inherited)

---

## 4. MODULE WRAPPING PATTERN (csdr/module/toolbox.py)

### ExecModule - External Program Wrapper

```python
from pycsdr.modules import ExecModule
from pycsdr.types import Format

class Rtl433Module(ExecModule):
    def __init__(self, sampleRate: int = 250000, jsonOutput: bool = False):
        cmd = [
            "rtl_433",                      # Binary name
            "-r", "cf32:-",                 # Read CF32 from stdin
            "-s", str(sampleRate),          # Sample rate
            "-M", "time:unix" if jsonOutput else "time:utc",
            "-F", "json" if jsonOutput else "kv",
            "-A", "-Y", "autolevel",        # Auto-level
        ]
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### Key ExecModule Constructor Parameters

1. **Input Format** - `Format.COMPLEX_FLOAT`, `Format.SHORT`, `Format.CHAR`, etc.
2. **Output Format** - Usually `Format.CHAR` for text output
3. **Command** - List of command + arguments

### LoRa Module Implementation

```python
class LoRaRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000, bandwidth: int = 125000,
                 spreadingFactor: int = 7, jsonOutput: bool = True):
        cmd = [
            "lorarx",           # Binary
            "-i", "-",          # IQ from stdin
            "-if", "f32",       # Float32 format
            "-r", str(sampleRate),
            "-b", str(bandwidth),
            "-s", str(spreadingFactor),
        ]
        if jsonOutput:
            cmd += ["-j"]       # JSON output
        
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### Format Types

```python
from pycsdr.types import Format

# Common formats
Format.COMPLEX_FLOAT      # IQ samples (cf32)
Format.COMPLEX_SHORT      # IQ samples (CS16)
Format.FLOAT              # Audio (f32)
Format.SHORT              # Audio (S16)
Format.CHAR               # Text output
```

### PopenModule - File I/O Wrapper

```python
class WavFileModule(PopenModule):
    def getInputFormat(self) -> Format:
        return Format.SHORT
    
    def start(self):
        super().start()
        # Write .WAV file header to stdin
        self.process.stdin.write(header)
```

---

## 5. DEMODULATOR CHAIN PATTERN (csdr/chain/toolbox.py)

### Base Demodulator Classes

```python
from csdr.chain.demodulator import (
    ServiceDemodulator,      # For background service modes
    DialFrequencyReceiver,   # Receives frequency updates
    SecondaryDemodulator,    # Secondary FFT support
)
from csdr.chain import Chain
```

### Demodulator Class Hierarchy

```
Chain (base)
  ├─ BaseDemodulatorChain
  ├─ SecondaryDemodulator
  │   ├─ ServiceDemodulator ⭐
  │   └─ ... other secondary demodulators
  └─ ... other chains
```

### ServiceDemodulator - Pattern for External Tools

```python
class IsmDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, sampleRate: int = 250000, service: bool = False):
        self.sampleRate = sampleRate
        self.parser = IsmParser(service=service)
        
        # List of processing modules (workers)
        workers = [
            Rtl433Module(self.sampleRate, jsonOutput=True),
            self.parser,
        ]
        
        # Initialize chain with workers
        super().__init__(workers)
    
    def getFixedAudioRate(self) -> int:
        """Return fixed sample rate for this decoder"""
        return self.sampleRate
    
    def supportsSquelch(self) -> bool:
        """Whether squelch is supported"""
        return False
    
    def setDialFrequency(self, frequency: int) -> None:
        """Called when user tunes frequency"""
        self.parser.setDialFrequency(frequency)
```

### LoRa Demodulator Implementation

```python
from csdr.chain.demodulator import ServiceDemodulator, DialFrequencyReceiver
from csdr.module.toolbox import LoRaRxModule
from owrx.toolbox import LoRaParser

class LoRaDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, sampleRate: int = 250000, service: bool = False):
        self.sampleRate = sampleRate
        self.parser = LoRaParser(service=service)
        
        workers = [
            LoRaRxModule(self.sampleRate, jsonOutput=True),
            self.parser,
        ]
        
        super().__init__(workers)
    
    def getFixedAudioRate(self) -> int:
        return self.sampleRate
    
    def supportsSquelch(self) -> bool:
        return False
    
    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)
```

### Chain Composition Pattern

Workers are connected in pipeline order:
```
IQ Input → Module1 → Module2 → Module3 → Output
                ↓        ↓        ↓
         (data flows through chain)
```

### Optional: MultimonDemodulator Pattern (with DSP)

```python
class MultimonDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, decoders: list[str], parser, withSquelch: bool = False):
        self.sampleRate = 22050
        self.squelch = None
        self.parser = parser
        
        workers = [
            FmDemod(),                    # Demodulate FM
            Convert(Format.FLOAT, Format.SHORT),  # Float → Short
            MultimonModule(decoders),     # Run multimon-ng
            self.parser,                  # Parse output
        ]
        
        # Optional squelch at beginning
        if withSquelch:
            self.squelch = Squelch(Format.COMPLEX_FLOAT, ...)
            workers.insert(0, self.squelch)
        
        super().__init__(workers)
```

---

## 6. DSP FACTORY PATTERN (owrx/dsp.py)

### Demodulator Factory Method

```python
class ClientDsp:
    def _getSecondaryDemodulator(self, mod: str) -> Optional[SecondaryDemodulator]:
        """Factory method - instantiate demodulator based on modulation string"""
        
        if isinstance(mod, SecondaryDemodulator):
            return mod
        
        # ISM pattern (external tool)
        elif mod == "ism":
            from csdr.chain.toolbox import IsmDemodulator
            return IsmDemodulator(250000)
        
        # LoRa pattern (external tool)
        elif mod == "lora":
            from csdr.chain.toolbox import LoRaDemodulator
            return LoRaDemodulator(service=True)
        
        # HFDL pattern (external tool with AGC)
        elif mod == "hfdl":
            from csdr.chain.toolbox import HfdlDemodulator
            return HfdlDemodulator()
        
        # Audio chopper pattern (WSJT-X modes)
        elif mod in ["ft8", "wspr", "jt65", "jt9", "ft4", "fst4", "fst4w", "q65"]:
            from csdr.chain.digimodes import AudioChopperDemodulator
            from owrx.wsjt import WsjtParser
            return AudioChopperDemodulator(mod, WsjtParser())
        
        return None
```

### Integration Points

1. **Mode Definition** - Mode registered in `Modes.mappings`
2. **Feature Detection** - Requirement name matches requirement method
3. **Factory Case** - Add elif branch with mode name
4. **Instantiation** - Return demodulator instance
5. **Parser** - Create parser instance in demodulator

---

## 7. COMPLETE INTEGRATION CHECKLIST FOR LoRa

### File 1: owrx/modes.py
```python
# Add to Modes.mappings list (1 line)
ServiceOnlyMode(
    "lora", "LoRa",
    underlying=["empty"],
    ifRate=250000,
    requirements=["lora"],
    service=True,
    squelch=False
),
```

### File 2: owrx/feature.py
```python
# Add to FeatureDetector.features dict (1 line)
"lora": ["lorarx"],

# Add requirement method (~5 lines)
def has_lorarx(self):
    """Install lorarx from http://oe5dxl.hamspirit.at:8025/aprs/bin/lorarx"""
    return self.command_is_runnable("lorarx --help")
```

### File 3: csdr/module/toolbox.py
```python
# Add module class (~10 lines)
class LoRaRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000, bandwidth: int = 125000,
                 spreadingFactor: int = 7, jsonOutput: bool = True):
        cmd = [
            "lorarx", "-i", "-", "-if", "f32",
            "-r", str(sampleRate), "-b", str(bandwidth),
            "-s", str(spreadingFactor),
        ]
        if jsonOutput:
            cmd += ["-j"]
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### File 4: csdr/chain/toolbox.py
```python
# Add demodulator class (~20 lines)
class LoRaDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, sampleRate: int = 250000, service: bool = False):
        self.sampleRate = sampleRate
        self.parser = LoRaParser(service=service)
        workers = [
            LoRaRxModule(self.sampleRate, jsonOutput=True),
            self.parser,
        ]
        super().__init__(workers)
    
    def getFixedAudioRate(self) -> int:
        return self.sampleRate
    
    def supportsSquelch(self) -> bool:
        return False
    
    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)
```

### File 5: owrx/toolbox.py
```python
# Add parser class (~20 lines)
class LoRaParser(TextParser):
    def __init__(self, service: bool = False):
        self.colors = ColorCache()
        super().__init__(filePrefix="LoRa", service=service)
    
    def parse(self, msg: bytes):
        out = json.loads(msg)
        out["mode"] = "LoRa"
        if "time" in out:
            out["timestamp"] = int(out["time"]) * 1000
            del out["time"]
        if self.frequency:
            out["freq"] = self.frequency
        ReportingEngine.getSharedInstance().spot(out)
        if not self.service and "from" in out:
            out["color"] = self.colors.getColor(out["from"])
        return out
```

### File 6: owrx/dsp.py
```python
# Add factory case in _getSecondaryDemodulator (~3 lines)
elif mod == "lora":
    from csdr.chain.toolbox import LoRaDemodulator
    return LoRaDemodulator(service=True)
```

---

## 8. KEY PATTERNS TO FOLLOW FOR NEW SIGNAL CLASSIFICATION

### Pattern 1: External Decoder Integration
**Used by:** ISM (rtl_433), LoRa, HFDL, VDL2, ACARS, ADS-B
**Steps:**
1. Define Mode with `underlying=["empty"]` and fixed `ifRate`
2. Add feature with binary dependency
3. Create ExecModule wrapping external tool's command
4. Create TextParser subclass parsing JSON output
5. Create ServiceDemodulator subclass composing Module + Parser
6. Add factory case in `_getSecondaryDemodulator()`

### Pattern 2: Audio Chopper (WSJT-X, JS8Call)
**Used by:** FT8, FT4, WSPR, JS8Call
**Steps:**
1. FM demodulate to get audio
2. Sample at fixed rate (e.g., 11025 Hz)
3. Write to external program's stdin
4. Parse decoded text output
5. Return JSON with decoded message

### Pattern 3: DSP Chain with Demodulation
**Used by:** Multimon (POCSAG, FLEX), CW Skimmer, RDS
**Steps:**
1. Apply DSP (FM demod, resampling, format conversion)
2. Pipe to external decoder
3. Parse decoder output
4. Support optional squelch

### Pattern 4: Specialized Chains
**For:** Complex hardware interfaces
- Add preprocessing (AGC, format conversion)
- Handle special output formats
- Manage state (e.g., satellite tracking)

---

## 9. SAMPLE LORARX OUTPUT (for parser testing)

```json
{
  "time": 1700000000,
  "freq": 433775000,
  "bandwidth": 125000,
  "sf": 7,
  "snr": 8.5,
  "rssi": -95,
  "from": "OE5DXL-1",
  "to": "APZMDM",
  "payload": "!4826.42N/01335.38E>Test LoRa APRS",
  "type": "aprs"
}
```

---

## 10. CRITICAL IMPLEMENTATION NOTES

### Sample Rate Management
- **IQ Input:** Usually 100-250 kHz for external decoders
- **Use `ifRate` in Mode** for fixed-rate decoders
- **FixedAudioRateChain** interface tells DSP to use specific rate

### Frequency Tracking
- Parser receives dial frequency via `setDialFrequency()`
- Set once per frequency change
- Used to annotate decoder output with actual frequency

### Service vs. Interactive Mode
- `service=True` → Background only, no client-side display
- `service=False` → User can select in UI
- Parser checks `self.service` to skip some output

### Error Handling
- Wrap `parse()` in try/except
- Log errors but don't crash
- Return None for unparseable lines

### Squelch Support
- Most external decoders don't support squelch
- Return `False` from `supportsSquelch()`
- Works fine - data just flows through

### Reporting
```python
ReportingEngine.getSharedInstance().spot(out)
```
- Reports decoded message to external services
- APRS-IS, MQTT, PSK Reporter, etc.
- Requires proper JSON format with mode, timestamp, etc.

---

## 11. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                  owrx/modes.py                              │
│  Define Mode + requirements ("lora" → ["lorarx"])          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────────┐
│              owrx/feature.py                                │
│  Check if requirement available (has_lorarx() method)      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────────┐
│              owrx/dsp.py                                    │
│  Factory: instantiate demodulator when mode selected        │
└────────────────┬──────────────────────────────┬─────────────┘
                 │                              │
      ┌──────────▼──────────┐      ┌────────────▼──────────┐
      │  ServiceDemodulator │      │  (other demodulator)  │
      │  (csdr/chain/)      │      │        types          │
      └──────────┬──────────┘      └───────────────────────┘
                 │
      ┌──────────┴─────────────────────────────────┐
      │                                            │
   ┌──▼──────────────────────┐    ┌──────────────▼─────┐
   │  LoRaRxModule            │    │  LoRaParser        │
   │  (ExecModule)            │    │  (TextParser)      │
   │                          │    │                    │
   │  Runs:                   │    │  - Parse JSON      │
   │  lorarx -i - -r 250000   │    │  - Add frequency   │
   │        -b 125000 -s 7    │    │  - Report to APRS  │
   └──────────┬───────────────┘    └────────┬───────────┘
              │                             │
        Binary stdin                  Parser stdout
              │                             │
        ┌─────▼─────────────────────────────▼──────┐
        │  IQ Samples → lorarx → JSON output       │
        └─────────────────────────────────────────┘
```

---

## 12. TESTING CHECKLIST

- [ ] Mode registered in `Modes.mappings`
- [ ] Feature detection method implemented
- [ ] ExecModule command-line arguments correct
- [ ] Parser handles sample decoder output
- [ ] Frequency gets passed to parser
- [ ] JSON output formatted correctly
- [ ] Service mode doesn't send to WebSocket
- [ ] Factory returns demodulator instance
- [ ] No syntax errors (flake8/black)
- [ ] External binary installed and runnable

