# OpenWebRX+ Signal Classification Implementation - Quick Reference

This document maps each implementation pattern to specific file locations with line numbers.

## File Map

### 1. Mode Definition - `/home/user/openwebrxplus/owrx/modes.py`

**Location:** Lines 37-358 (Modes.mappings list)

**Key Examples:**
- Line 124-142: Analog modes (FM, WFM, AM, etc.)
- Line 145-151: Basic digital modes (BPSK31, BPSK63, RTTY)
- Line 153-162: WSJT modes (FT8, FT4, WSPR, JS8Call)
- Line 194-258: Service-only modes (POCSAG, ISM, ADSB)

**Pattern Template:**
```python
# At line 195-257, observe ISM mode pattern:
DigitalMode(
    "ism",
    "ISM",
    underlying=["empty"],
    bandpass=None,
    ifRate=250000,
    requirements=["ism"],
    service=True,
    squelch=False
),
```

---

### 2. Feature Detection - `/home/user/openwebrxplus/owrx/feature.py`

**Feature Registry Location:** Lines 52-108

**Detection Methods:**
- Line 131-132: `is_available()` - Check if all requirements met
- Line 143-147: `has_requirements()` - Check list of requirements
- Line 155-168: `has_requirement()` - Lookup and cache single requirement
- Line 173-201: `command_is_runnable()` - Shell execution check

**Example Methods:**
- Line 675-682: `has_rtl_433()` - ISM decoder detection
- Line 659-673: `has_dump1090()` - ADS-B decoder detection
- Line 810-816: `has_lame()` - MP3 encoder detection

**Pattern Template - Add to features dict (Line 52-108):**
```python
"lora": ["lorarx"],
```

**Pattern Template - Add method after line 816:**
```python
def has_lorarx(self):
    """OpenWebRX uses lorarx to decode LoRa signals"""
    return self.command_is_runnable("lorarx --help")
```

---

### 3. Parsers - `/home/user/openwebrxplus/owrx/toolbox.py`

**Base Class:** Lines 40-62 (TextParser)

**Key Methods:**
- Line 55-56: `parse(msg: bytes)` - Override to parse decoder output
- Line 58-62: `process(line: bytes)` - Line processing with error handling
- Line 46-52: `myName()` - Debug output string

**Real Parser Examples:**
- Lines 122-147: `IsmParser` - ISM (rtl_433) decoder parser
- Lines 150-194: `PageParser` - POCSAG/FLEX parser
- Lines 336-374: `EasParser` - Emergency alert parser
- Lines 377-411: `CwSkimmerParser` - CW skimmer parser

**Key IsmParser Pattern (Lines 122-147):**
```python
class IsmParser(TextParser):
    def __init__(self, service: bool = False):
        self.colors = ColorCache()
        super().__init__(filePrefix="ISM", service=service)
    
    def parse(self, msg: bytes):
        out = json.loads(msg)                      # Line 131
        out["mode"] = "ISM"                        # Line 133
        if "time" in out:                          # Line 135-137
            out["timestamp"] = int(out["time"]) * 1000
            del out["time"]
        if self.frequency:                         # Line 139-140
            out["freq"] = self.frequency
        ReportingEngine.getSharedInstance().spot(out)  # Line 142
        if not self.service:                       # Line 144-145
            out["color"] = self.colors.getColor(out["id"])
        return out                                 # Line 147
```

---

### 4. ExecModule Wrappers - `/home/user/openwebrxplus/csdr/module/toolbox.py`

**Location:** Lines 1-187

**Module Examples:**
- Lines 7-16: `Rtl433Module` - ISM signal decoder (rtl_433)
- Lines 28-36: `DumpHfdlModule` - HFDL aircraft decoder
- Lines 39-47: `DumpVdl2Module` - VDL2 aircraft decoder
- Lines 50-71: `Dump1090Module` - ADS-B aircraft decoder
- Lines 123-126: `CwSkimmerModule` - CW decoder
- Lines 155-161: `LameModule` - MP3 encoder

**Key Pattern (Rtl433Module, Lines 7-16):**
```python
class Rtl433Module(ExecModule):
    def __init__(self, sampleRate: int = 250000, jsonOutput: bool = False):
        cmd = [
            "rtl_433", "-r", "cf32:-", "-s", str(sampleRate),
            "-M", "time:unix" if jsonOutput else "time:utc",
            "-F", "json" if jsonOutput else "kv",
            "-A", "-Y", "autolevel",
        ]
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

**Format Types Available:**
```python
from pycsdr.types import Format

# Input/Output formats used in ExecModule
Format.COMPLEX_FLOAT      # IQ samples (cf32)
Format.COMPLEX_SHORT      # IQ samples (CS16)
Format.FLOAT              # Audio (f32)
Format.SHORT              # Audio (S16)
Format.CHAR               # Text output
```

---

### 5. Demodulator Chains - `/home/user/openwebrxplus/csdr/chain/toolbox.py`

**Location:** Lines 1-369

**Base Class Interfaces (imported from demodulator.py):**
- `ServiceDemodulator` - For background services
- `DialFrequencyReceiver` - Receives frequency updates
- `FixedAudioRateChain` - Provides fixed sample rate

**Demodulator Examples:**
- Lines 17-35: `IsmDemodulator` - Pattern for external decoder (rtl_433)
- Lines 38-81: `MultimonDemodulator` - Pattern with DSP chain
- Lines 124-143: `HfdlDemodulator` - External tool with AGC
- Lines 169-189: `AdsbDemodulator` - Fixed-rate service
- Lines 214-233: `RdsDemodulator` - Audio decoder pattern
- Lines 236-257: `CwSkimmerDemodulator` - CW decoder pattern

**Key IsmDemodulator Pattern (Lines 17-35) - YOUR TEMPLATE:**
```python
class IsmDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, sampleRate: int = 250000, service: bool = False):
        self.sampleRate = sampleRate
        self.parser = IsmParser(service=service)
        workers = [
            Rtl433Module(self.sampleRate, jsonOutput = True),
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

---

### 6. DSP Factory - `/home/user/openwebrxplus/owrx/dsp.py`

**Factory Method:** Lines 664-779 (`_getSecondaryDemodulator`)

**Location of Demodulator Cases:**
- Line 741-743: ISM demodulator case
- Line 748-750: HFDL demodulator case
- Line 751-753: VDL2 demodulator case
- Line 754-756: ACARS demodulator case
- Line 757-759: ADS-B demodulator case
- Line 760-763: Audio recording demodulator case

**Key Pattern (ISM, Lines 741-743):**
```python
elif mod == "ism":
    from csdr.chain.toolbox import IsmDemodulator
    return IsmDemodulator(250000)
```

---

### 7. Base Demodulator Classes - `/home/user/openwebrxplus/csdr/chain/demodulator.py`

**Interface Definitions:**
- Lines 6-9: `FixedAudioRateChain` - Must implement `getFixedAudioRate()`
- Lines 12-15: `FixedIfSampleRateChain` - Must implement `getFixedIfSampleRate()`
- Lines 18-21: `DialFrequencyReceiver` - Must implement `setDialFrequency()`
- Lines 64-69: `BaseDemodulatorChain` - Base class for primary demodulators
- Lines 72-80: `SecondaryDemodulator` - Base for service demodulators
- Lines 83-84: `ServiceDemodulator` - Convenience for service decoders

---

## Integration Summary

### Files to Modify (6 total)

| File | Lines | Change | Code Lines |
|------|-------|--------|-----------|
| owrx/modes.py | 195-257 | Add ServiceOnlyMode | 1 |
| owrx/feature.py | 52-108 | Add to features dict | 1 |
| owrx/feature.py | 810+ | Add has_* method | 3-5 |
| csdr/module/toolbox.py | 187+ | Add ExecModule class | 10-15 |
| csdr/chain/toolbox.py | 369+ | Add ServiceDemodulator | 20-25 |
| owrx/toolbox.py | 411+ | Add TextParser class | 20-30 |
| owrx/dsp.py | 741-743 | Add factory case | 3 |

**Total:** ~80-100 lines of code

---

## Code Structure in Each File

### owrx/modes.py Structure
```
1-12:     Imports
13-36:    Mode and Bandpass classes
37-358:   Modes.mappings = [ ... ]
360-381:  Modes static methods
```

### owrx/feature.py Structure
```
1-50:     Imports and caching classes
51-108:   FeatureDetector.features dict
110-171:  Feature checking methods
173-202:  command_is_runnable helper
203-825:  Individual requirement methods (has_*)
```

### owrx/toolbox.py Structure
```
1-15:     Imports
18-38:    Mp3Recorder class
40-86:    TextParser base class
88-120:   RdsParser example
122-148:  IsmParser example
150-303:  PageParser example
305-334:  SelCallParser example
336-375:  EasParser example
377-412:  CwSkimmerParser example
```

### csdr/module/toolbox.py Structure
```
1-5:      Imports
7-16:     Rtl433Module
19-25:    MultimonModule
28-36:    DumpHfdlModule
39-47:    DumpVdl2Module
50-71:    Dump1090Module
107-121:  AcarsDecModule
123-126:  CwSkimmerModule
129-134:  RedseaModule
137-152:  DablinModule
155-161:  LameModule
164-187:  SatDumpModule
```

### csdr/chain/toolbox.py Structure
```
1-7:      Imports
17-35:    IsmDemodulator
38-81:    MultimonDemodulator
83-94:    PageDemodulator
97-103:   SelCallDemodulator
106-112:  EasDemodulator
115-121:  ZveiDemodulator
124-143:  HfdlDemodulator
146-166:  Vdl2Demodulator
169-189:  AdsbDemodulator
192-211:  AcarsDemodulator
214-233:  RdsDemodulator
236-257:  CwSkimmerDemodulator
260-297:  AudioRecorder
299-369:  Weather satellite demodulators
```

### owrx/dsp.py Structure
```
1-70:     Imports and ClientDemodulatorChain class
100-350:  ClientDemodulatorChain methods
664-779:  _getSecondaryDemodulator factory method
781+:     setSecondaryDemodulator and other methods
```

---

## Quick Copy-Paste Templates

### Mode Definition
```python
ServiceOnlyMode(
    "lora",
    "LoRa",
    underlying=["empty"],
    bandpass=None,
    ifRate=250000,
    requirements=["lora"],
    service=True,
    squelch=False
),
```

### Feature Detection
```python
# In features dict
"lora": ["lorarx"],

# New method
def has_lorarx(self):
    """LoRa decoder from http://oe5dxl.hamspirit.at:8025/aprs/bin/lorarx"""
    return self.command_is_runnable("lorarx --help")
```

### ExecModule
```python
from pycsdr.modules import ExecModule
from pycsdr.types import Format

class LoRaRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000, jsonOutput: bool = True):
        cmd = [
            "lorarx", "-i", "-", "-if", "f32",
            "-r", str(sampleRate), "-j" if jsonOutput else "-kv"
        ]
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### TextParser
```python
from owrx.toolbox import TextParser
from owrx.reporting import ReportingEngine
from owrx.color import ColorCache
import json

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

### ServiceDemodulator
```python
from csdr.chain.demodulator import ServiceDemodulator, DialFrequencyReceiver

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

### DSP Factory Case
```python
elif mod == "lora":
    from csdr.chain.toolbox import LoRaDemodulator
    return LoRaDemodulator(service=True)
```

---

## Testing Each Component

### Test Feature Detection
```bash
python3 -c "from owrx.feature import FeatureDetector; f = FeatureDetector(); print('lorarx available:', f.is_available('lora'))"
```

### Test Mode Registration
```bash
python3 -c "from owrx.modes import Modes; modes = [m.modulation for m in Modes.getModes()]; print('lora' in modes)"
```

### Test Parser Directly
```python
from owrx.toolbox import LoRaParser
import json

parser = LoRaParser(service=False)
parser.frequency = 433775000

sample_json = b'{"time": 1700000000, "from": "TEST", "payload": "test"}'
result = parser.parse(sample_json)
print(result)
```

### Test Demodulator Factory
```python
from owrx.dsp import ClientDsp

dsp = ClientDsp()
demod = dsp._getSecondaryDemodulator("lora")
print("Demodulator:", demod)
print("Sample rate:", demod.getFixedAudioRate())
```

---

## Common Issues & Solutions

### Issue: Parser not receiving JSON
**Solution:** Verify ExecModule output format is `Format.CHAR` and decoder outputs valid JSON

### Issue: Feature detection always False
**Solution:** Ensure `has_lorarx()` method is implemented and binary is in PATH

### Issue: Frequency not updating
**Solution:** Verify demodulator implements `DialFrequencyReceiver` and calls `parser.setDialFrequency()`

### Issue: Service data appearing in UI
**Solution:** Use `service=True` in Mode definition and check parser's `self.service` flag

### Issue: Squelch not working
**Solution:** Return `False` from `supportsSquelch()` for external decoders

---

## Documentation References

- Design document: `/home/user/openwebrxplus/docs/lora/lora-implementation-design.md`
- Architecture doc: `/home/user/openwebrxplus/docs/claude/architecture.md`
- This quick ref: `/home/user/openwebrxplus/docs/PATTERN_SUMMARY.md`

