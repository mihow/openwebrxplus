# LoRa Implementation Quick Start Guide

**Implementation Method:** lorarx (Recommended - Option 1)
**Estimated Time:** 2-3 days
**Difficulty:** Easy (follows existing patterns)

---

## Overview

This guide provides step-by-step instructions to add LoRa support to OpenWebRX+ using the lorarx standalone decoder, following the same pattern as ISM/rtl_433 integration.

---

## Prerequisites

```bash
# Install lorarx binary
wget http://oe5dxl.hamspirit.at:8025/aprs/bin/lorarx
chmod +x lorarx
sudo mv lorarx /usr/local/bin/

# Verify installation
lorarx --help
```

---

## Implementation Steps

### Step 1: Add Mode Definition (owrx/modes.py)

**Location:** Line ~180 (with other ServiceOnlyMode definitions)

```python
# Add after other service modes
ServiceOnlyMode("lora", "LoRa", requirements=["lora"]),
```

### Step 2: Add Feature Detection (owrx/feature.py)

**Location:** Inside the `features` dictionary (~line 55)

```python
class FeatureDetector(object):
    features = {
        # ... existing features ...
        "lora": ["lorarx"],  # Check for lorarx binary
    }
```

### Step 3: Create LoRaRx Module (csdr/module/toolbox.py)

**Location:** After other ExecModule classes (after Rtl433Module, ~line 25)

```python
class LoRaRxModule(ExecModule):
    """
    Wrapper for lorarx LoRa decoder
    Supports LoRaWAN, LoRa APRS, Meshtastic, FANET
    """
    def __init__(self, sampleRate: int = 250000, bandwidth: int = 125000,
                 spreadingFactor: int = 7, jsonOutput: bool = True):
        """
        Initialize lorarx decoder module

        Args:
            sampleRate: IQ sample rate (default 250kHz)
            bandwidth: LoRa bandwidth in Hz (7800, 10400, 15600, 20800, 31250,
                       41700, 62500, 125000, 250000, 500000)
            spreadingFactor: LoRa spreading factor (7-12)
            jsonOutput: Enable JSON output format
        """
        cmd = [
            "lorarx",
            "-i", "-",                      # IQ data from stdin
            "-if", "f32",                   # Input format: float32 (complex)
            "-r", str(sampleRate),          # Sample rate
            "-b", str(bandwidth // 1000),   # Bandwidth in kHz
            "-s", str(spreadingFactor),     # Spreading factor
            "-cd", "1",                     # Coding rate denominator (4/5 = CR1)
            "-lf",                          # Low frequency mode
        ]
        if jsonOutput:
            cmd += ["-j"]                   # JSON output

        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### Step 4: Create Demodulator Chain (csdr/chain/toolbox.py)

**Location:** After other demodulator classes (after IsmDemodulator, ~line 35)

```python
class LoRaDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    """
    LoRa demodulator chain using lorarx
    Decodes LoRaWAN, LoRa APRS, Meshtastic, FANET packets
    """
    def __init__(self, sampleRate: int = 250000, service: bool = False):
        """
        Initialize LoRa demodulator

        Args:
            sampleRate: IQ sample rate (default 250kHz for 125kHz bandwidth)
            service: True if running as background service
        """
        self.sampleRate = sampleRate
        self.parser = LoRaParser(service=service)

        workers = [
            LoRaRxModule(self.sampleRate, jsonOutput=True),
            self.parser,
        ]

        super().__init__(workers)

    def getFixedAudioRate(self) -> int:
        """Return required sample rate"""
        return self.sampleRate

    def supportsSquelch(self) -> bool:
        """LoRa decoder does not support squelch"""
        return False

    def setDialFrequency(self, frequency: int) -> None:
        """Set frequency for parser metadata"""
        self.parser.setDialFrequency(frequency)
```

**Don't forget to add the import at the top of the file:**

```python
# Add to imports at line ~2
from owrx.toolbox import LoRaParser
```

### Step 5: Create Parser (owrx/toolbox.py)

**Location:** After other parser classes (after IsmParser, ~line 200)

```python
class LoRaParser(TextParser):
    """
    Parser for lorarx JSON output
    Handles LoRaWAN, LoRa APRS, Meshtastic, and FANET packets
    """
    def __init__(self, service: bool = False):
        """
        Initialize LoRa parser

        Args:
            service: True if running as background service
        """
        # Colors will be assigned via this cache
        self.colors = ColorCache()
        # Construct parent object
        super().__init__(filePrefix="LoRa", service=service)

    def parse(self, msg: bytes):
        """
        Parse lorarx JSON output

        Expected JSON format from lorarx:
        {
            "time": <unix_timestamp>,
            "freq": <frequency_hz>,
            "bandwidth": <bw_hz>,
            "sf": <spreading_factor>,
            "snr": <snr_db>,
            "rssi": <rssi_dbm>,
            "from": "<sender_id>",
            "to": "<destination_id>",
            "payload": "<decoded_payload>",
            "type": "aprs|lorawan|meshtastic|fanet"
        }
        """
        try:
            # Expect JSON data in text form
            out = json.loads(msg)

            # Add mode name
            out["mode"] = "LoRa"

            # Convert Unix timestamps to milliseconds
            if "time" in out:
                out["timestamp"] = int(out["time"]) * 1000
                del out["time"]

            # Add frequency, if known
            if self.frequency:
                out["freq"] = self.frequency

            # Report message to external services
            ReportingEngine.getSharedInstance().spot(out)

            # In interactive mode, color messages based on sender IDs
            if not self.service:
                sender_id = out.get("from", out.get("sender", "unknown"))
                out["color"] = self.colors.getColor(sender_id)

            # Always return JSON data
            return out

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LoRa JSON: %s", e)
            return {}
        except Exception as e:
            logger.error("Error parsing LoRa data: %s", e)
            return {}
```

**Don't forget the import at the top:**

```python
# Should already be imported, but verify:
import json
```

### Step 6: Add Demodulator Factory (owrx/dsp.py)

**Location:** In `_getSecondaryDemodulator()` method (~line 750)

Find this method and add the LoRa case:

```python
def _getSecondaryDemodulator(self, mod: str):
    # ... existing code ...

    elif mod == "ism":
        from csdr.chain.toolbox import IsmDemodulator
        return IsmDemodulator(service=True)

    # ADD THIS BLOCK:
    elif mod == "lora":
        from csdr.chain.toolbox import LoRaDemodulator
        return LoRaDemodulator(service=True)

    # ... rest of existing code ...
```

---

## Testing

### 1. Verify Feature Detection

```bash
python3 -m owrx.feature
```

Should show:
```
...
lora: ✓ (lorarx found)
...
```

### 2. Add Bookmark

Create or edit a bookmark file in `bookmarks.d/`:

```json
{
  "name": "LoRa APRS EU",
  "bookmarks": [
    {
      "name": "LoRa APRS 433.775",
      "frequency": 433775000,
      "modulation": "lora"
    }
  ]
}
```

### 3. Start OpenWebRX+

```bash
python3 openwebrx.py
```

### 4. Test Reception

1. Navigate to http://localhost:8073
2. Click on "LoRa APRS 433.775" bookmark
3. Verify mode shows "LoRa"
4. If you have a LoRa transmitter nearby, you should see decoded packets

---

## Configuration Options

### Advanced lorarx Parameters

To support multiple bandwidths and spreading factors, modify `LoRaRxModule`:

```python
class LoRaRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000,
                 bandwidth: int = 125000,
                 spreadingFactor: int = 7,
                 codingRate: int = 1,  # 4/5
                 implicitHeader: bool = False,
                 invertIQ: bool = False,
                 jsonOutput: bool = True):
        cmd = [
            "lorarx",
            "-i", "-",
            "-if", "f32",
            "-r", str(sampleRate),
            "-b", str(bandwidth // 1000),
            "-s", str(spreadingFactor),
            "-cd", str(codingRate),
        ]

        if implicitHeader:
            cmd += ["-ih"]

        if invertIQ:
            cmd += ["-iq"]

        if jsonOutput:
            cmd += ["-j"]

        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

### Multi-Bandwidth Support

To monitor multiple bandwidths simultaneously, you would need multiple service instances:

```python
# In configuration
"lora_services": [
    {"bandwidth": 125000, "sf": 7, "frequency": 433775000},
    {"bandwidth": 125000, "sf": 8, "frequency": 433775000},
    {"bandwidth": 125000, "sf": 9, "frequency": 433775000},
]
```

This would require additional changes to the service management code.

---

## Troubleshooting

### lorarx not found

```bash
# Verify installation
which lorarx

# Check PATH
echo $PATH

# Manually specify path in feature detection
# Edit owrx/feature.py:
"lora": ["/usr/local/bin/lorarx"],
```

### No packets decoded

1. **Check frequency:** Verify you're on the correct LoRa frequency
2. **Check bandwidth:** LoRa transmitter and receiver must match BW/SF
3. **Check transmitter:** Ensure LoRa transmitter is active and in range
4. **Check sample rate:** Should be at least 2x the bandwidth
5. **Check lorarx logs:** Run lorarx manually to see raw output

### Manual Testing

Test lorarx directly with IQ file:

```bash
# Record IQ samples with RTL-SDR
rtl_sdr -f 433775000 -s 250000 -n 25000000 lora_test.cf32

# Decode with lorarx
cat lora_test.cf32 | lorarx -i - -if f32 -r 250000 -b 125 -s 7 -j
```

---

## Performance Considerations

### Sample Rate

- **125 kHz bandwidth:** 250 kHz sample rate (recommended)
- **250 kHz bandwidth:** 500 kHz sample rate
- **500 kHz bandwidth:** 1 MHz sample rate

### CPU Usage

- Minimal: lorarx is efficient (~5-10% CPU per instance)
- Can run multiple instances for different SF/BW combinations

### Memory Usage

- Low: ~10-20 MB per lorarx instance

---

## Common LoRa Frequencies

### Europe (433/868 MHz)
```json
[
  {"name": "LoRa APRS 433", "frequency": 433775000, "modulation": "lora"},
  {"name": "LoRaWAN 868.1", "frequency": 868100000, "modulation": "lora"},
  {"name": "LoRaWAN 868.3", "frequency": 868300000, "modulation": "lora"},
  {"name": "LoRaWAN 868.5", "frequency": 868500000, "modulation": "lora"}
]
```

### US (915 MHz)
```json
[
  {"name": "LoRaWAN 902.3", "frequency": 902300000, "modulation": "lora"},
  {"name": "LoRaWAN 902.5", "frequency": 902500000, "modulation": "lora"},
  {"name": "LoRa APRS 927.9", "frequency": 927900000, "modulation": "lora"}
]
```

### Meshtastic
```json
[
  {"name": "Meshtastic EU 869.525", "frequency": 869525000, "modulation": "lora"},
  {"name": "Meshtastic US 906.875", "frequency": 906875000, "modulation": "lora"}
]
```

---

## Next Steps

Once basic implementation is working:

1. **Add configuration UI:** Settings for BW/SF/CR in web interface
2. **Add statistics:** Packet count, SNR histogram, RSSI graphs
3. **LoRaWAN decoding:** Display DevEUI, AppEUI, frame counters
4. **APRS integration:** Forward LoRa APRS to existing APRS map
5. **Meshtastic mesh:** Display mesh network topology
6. **Multi-channel:** Decode multiple SF simultaneously

---

## Code Review Checklist

Before committing:

- [ ] All imports added correctly
- [ ] Feature detection working (`python3 -m owrx.feature`)
- [ ] Mode appears in available modes list
- [ ] Parser handles malformed JSON gracefully
- [ ] Logging added for debugging
- [ ] Code follows OpenWebRX+ style (black/flake8)
- [ ] No security issues (command injection, etc.)
- [ ] Documentation added
- [ ] Bookmarks added for common frequencies
- [ ] Tested with real LoRa hardware

---

## Git Commit Strategy

Suggested commits:

```bash
# Commit 1: Core infrastructure
git add owrx/modes.py owrx/feature.py
git commit -m "Add LoRa mode definition and feature detection"

# Commit 2: Decoder module
git add csdr/module/toolbox.py
git commit -m "Add lorarx decoder module wrapper"

# Commit 3: Demodulator chain
git add csdr/chain/toolbox.py
git commit -m "Add LoRa demodulator chain"

# Commit 4: Parser
git add owrx/toolbox.py
git commit -m "Add LoRa JSON parser"

# Commit 5: Integration
git add owrx/dsp.py
git commit -m "Integrate LoRa demodulator into DSP factory"

# Commit 6: Bookmarks
git add bookmarks.d/lora.json
git commit -m "Add LoRa frequency bookmarks"

# Commit 7: Documentation
git add docs/lora-*.md
git commit -m "Add LoRa implementation documentation"
```

---

## Files Modified Summary

| File | Lines Added | Purpose |
|------|-------------|---------|
| owrx/modes.py | 1 | Mode definition |
| owrx/feature.py | 1 | Feature detection |
| csdr/module/toolbox.py | ~25 | lorarx wrapper |
| csdr/chain/toolbox.py | ~30 | Demodulator chain |
| owrx/toolbox.py | ~35 | JSON parser |
| owrx/dsp.py | 3 | Factory instantiation |
| bookmarks.d/lora.json | ~20 | Frequency bookmarks |
| **Total** | **~115 lines** | |

---

## Support Resources

- **lorarx Documentation:** https://dxlwiki.dl1nux.de/index.php?title=Lorarx
- **LoRa APRS:** https://lora-aprs.info/
- **OpenWebRX+ GitHub:** https://github.com/luarvique/openwebrxplus
- **CLAUDE.md:** Project-specific guidelines

---

## Success Criteria

Implementation is complete when:

- ✅ Feature detection shows lorarx available
- ✅ LoRa mode appears in mode list
- ✅ Can decode LoRa APRS packets
- ✅ Can decode LoRaWAN packets
- ✅ Packets display in message panel with correct formatting
- ✅ Background service mode works
- ✅ No errors in logs during normal operation
- ✅ Code passes linting (black, flake8)
- ✅ Documentation added

---

## Estimated Timeline

- **Hour 1-2:** Setup and basic implementation (Steps 1-6)
- **Hour 3-4:** Testing and debugging
- **Hour 5-6:** Configuration and bookmarks
- **Hour 7-8:** Documentation and code review
- **Day 2:** Real-world testing with LoRa hardware
- **Day 3:** Refinement and additional features

**Total: 2-3 days for complete implementation**

---

Good luck with the implementation! Follow the patterns from existing decoders (ISM, PAGE) and you'll have LoRa support working quickly.
