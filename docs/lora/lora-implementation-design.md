# LoRa Support Implementation Design for OpenWebRX+

**Date:** 2025-11-19
**Author:** AI Design Analysis
**Status:** Design Phase

## Executive Summary

This document outlines four possible approaches for adding LoRa (Long Range) support to OpenWebRX+, a web-based SDR receiver. LoRa uses Chirp Spread Spectrum (CSS) modulation and is widely used for IoT applications (LoRaWAN, LoRa APRS, Meshtastic, etc.).

## Background

### What is LoRa?

- **Modulation:** Chirp Spread Spectrum (CSS)
- **Frequency Bands:** 433 MHz, 868 MHz (EU), 915 MHz (US), etc.
- **Bandwidth:** 7.8 kHz to 500 kHz
- **Spreading Factors:** SF7-SF12 (higher = longer range, lower data rate)
- **Use Cases:** LoRaWAN, LoRa APRS, Meshtastic, FANET, IoT sensors

### LoRa Licensing & Open Source Status

**IMPORTANT CLARIFICATION:** The statement *"LoRa is proprietary with no licensed software implementation available"* is **misleading**.

#### What's Proprietary vs. Open

**LoRa Physical Layer (Modulation) - PROPRIETARY:**
- ✅ **Patented by Semtech Corporation** (acquired from Cycleo SAS in 2012)
- ✅ **Chirp Spread Spectrum (CSS) modulation is patented**
- ✅ **Official hardware requires Semtech chipsets** (SX1272, SX1276, SX1278, etc.)
- ❌ **NOT open source** - No official specifications published by Semtech
- ⚠️ **Patents active** - US Patent #20160094269A1 and others

**LoRaWAN Protocol Layer - OPEN STANDARD:**
- ✅ **Open standard managed by LoRa Alliance** (non-profit)
- ✅ **Freely available specifications** (v1.0, v1.0.4, v1.1) - Download from lora-alliance.org
- ✅ **ITU-approved standard** (December 2021) - Official recognition as LPWAN standard
- ✅ **Open source implementations exist** - IBM's "LoRaWAN in C" (Eclipse Public License)
- ✅ **No licensing fees** for protocol implementation

#### Open Source Software Implementations - AVAILABLE ✅

**Contrary to the claim, multiple open-source LoRa decoders DO exist:**

1. **lorarx** (OE5DXL) - Standalone decoder
   - **Status:** Available, actively maintained (2024)
   - **License:** TBD (need to verify, but freely distributed)
   - **Legality:** Reverse-engineered, legal gray area
   - **Usage:** Widely used in amateur radio community

2. **gr-lora_sdr** (EPFL) - GNU Radio implementation
   - **Status:** Open source, GitHub available
   - **License:** GPL-3.0
   - **Legality:** Reverse-engineered for research/education
   - **Academic:** Published research with full implementation

3. **gr-lora** (rpp0) - Original GNU Radio blocks
   - **Status:** Open source, GitHub available
   - **License:** GPL-3.0
   - **Legality:** Reverse-engineered, widely used

4. **Python libraries** - Various SDR implementations
   - **pyLoRa:** Hardware interface library (not full demodulator)
   - **Research implementations:** Academic papers include code

#### Legal Gray Area

**The Reality:**
- ⚠️ These implementations **reverse-engineered** the LoRa modulation
- ⚠️ Semtech holds patents but **has not sued open source projects**
- ⚠️ **Non-commercial use** (amateur radio, research) generally tolerated
- ⚠️ **Commercial use** could face patent challenges
- ✅ **LoRaWAN protocol** itself is freely implementable

#### Why This Matters for OpenWebRX+

**OpenWebRX+ is well-positioned:**
- ✅ **Non-commercial, open-source project** - Lower legal risk
- ✅ **Receive-only** - Not competing with Semtech hardware sales
- ✅ **Uses existing decoders** - Not creating new reverse-engineering
- ✅ **Amateur radio / SDR community** - Established precedent
- ✅ **Educational/research focus** - Protected under fair use in many jurisdictions

**Recommendation:** Proceed with implementation using existing open-source decoders (lorarx, gr-lora_sdr). The amateur radio and SDR communities have used these for years without legal issues.

#### What You CAN and CANNOT Do

**✅ LEGAL/SAFE:**
- Receive and decode LoRa signals for personal/educational use
- Use open-source decoders (lorarx, gr-lora_sdr)
- Implement LoRaWAN protocol (open standard)
- Contribute to open-source projects
- Research and education

**⚠️ GRAY AREA:**
- Distribute software with LoRa demodulation
- Commercial products using reverse-engineered LoRa
- Creating new LoRa transmitters

**❌ CLEARLY RESTRICTED:**
- Selling devices that infringe Semtech patents
- Calling your product "LoRa certified" without LoRa Alliance approval
- Commercial LoRa hardware without Semtech licensing

#### References
- Semtech LoRa Patents: US Patent #20160094269A1 (and others)
- LoRa Alliance Specifications: https://lora-alliance.org/resource_hub/
- ITU Recognition: ITU-T Y.4480 (December 2021)
- Academic Research: "From Demodulation to Decoding: Toward Complete LoRa PHY Understanding" (ACM TOSN)

### OpenWebRX+ Decoder Integration Pattern

Based on code analysis, the integration follows a **5-layer architecture**:

```
1. Mode Definition (owrx/modes.py) - Declare mode metadata
         ↓
2. Feature Detection (owrx/feature.py) - Link to binary dependencies
         ↓
3. DSP Factory (owrx/dsp.py) - Instantiate demodulator on demand
         ↓
4. Demodulator Chain (csdr/chain/toolbox.py) - Compose DSP modules
         ↓
5. Output Parser (owrx/toolbox.py) - Parse decoder output → JSON
```

**Key Insight:** External decoders work via stdin/stdout pipes - no special APIs needed.

---

## Implementation Options

### Option 1: lorarx (Standalone CLI Tool) ⭐ **RECOMMENDED**

**Overview:** Use `lorarx`, a standalone command-line LoRa decoder that can decode LoRaWAN, LoRa APRS, Meshcom, and FANET.

#### Pros
- ✅ **Simplest integration** - Follows ISM/rtl_433 pattern exactly
- ✅ **Feature-complete** - Supports LoRaWAN, LoRa APRS, Meshcom, FANET
- ✅ **JSON output** - Easy parsing
- ✅ **Actively maintained** (updated 2024)
- ✅ **~100 lines of code** total integration

#### Cons
- ❌ External dependency (must be installed)
- ❌ Less control over demodulation parameters
- ❌ Documentation primarily in German

#### Integration Architecture

```
IQ Samples → LoRaRxModule (ExecModule) → lorarx binary → JSON output → LoRaParser → WebSocket
```

#### Implementation Details

**Files to Create/Modify (6 files, ~100 lines):**

1. **owrx/modes.py** - Add mode definition
```python
ServiceOnlyMode("lora", "LoRa", requirements=["lora"]),
```

2. **owrx/feature.py** - Add feature detection
```python
class FeatureDetector(object):
    features = {
        # ... existing features ...
        "lora": ["lorarx"],  # Check for lorarx binary
    }
```

3. **csdr/module/toolbox.py** - Create LoRaRx module
```python
class LoRaRxModule(ExecModule):
    def __init__(self, sampleRate: int = 250000, bandwidth: int = 125000,
                 spreadingFactor: int = 7, jsonOutput: bool = True):
        cmd = [
            "lorarx", "-i", "-",           # IQ from stdin
            "-if", "f32",                   # Format: float32
            "-r", str(sampleRate),          # Sample rate
            "-b", str(bandwidth),           # Bandwidth (kHz)
            "-s", str(spreadingFactor),     # Spreading factor
        ]
        if jsonOutput:
            cmd += ["-j"]  # JSON output
        super().__init__(Format.COMPLEX_FLOAT, Format.CHAR, cmd)
```

4. **csdr/chain/toolbox.py** - Create demodulator chain
```python
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

5. **owrx/toolbox.py** - Create parser
```python
class LoRaParser(TextParser):
    def __init__(self, service: bool = False):
        self.colors = ColorCache()
        super().__init__(filePrefix="LoRa", service=service)

    def parse(self, msg: bytes):
        out = json.loads(msg)
        out["mode"] = "LoRa"

        # Convert timestamp if needed
        if "time" in out:
            out["timestamp"] = int(out["time"]) * 1000
            del out["time"]

        # Add frequency
        if self.frequency:
            out["freq"] = self.frequency

        # Report to external services
        ReportingEngine.getSharedInstance().spot(out)

        # Color by sender ID in interactive mode
        if not self.service and "from" in out:
            out["color"] = self.colors.getColor(out["from"])

        return out
```

6. **owrx/dsp.py** - Add to demodulator factory
```python
def _getSecondaryDemodulator(self, mod: str):
    # ... existing code ...
    elif mod == "lora":
        from csdr.chain.toolbox import LoRaDemodulator
        return LoRaDemodulator(service=True)
```

#### Installation Requirements

```bash
# Download and install lorarx
wget http://oe5dxl.hamspirit.at:8025/aprs/bin/lorarx
chmod +x lorarx
sudo mv lorarx /usr/local/bin/

# Verify installation
lorarx --help
```

#### Configuration

Users would configure LoRa frequencies in bookmarks:

```json
{
  "name": "LoRa APRS EU",
  "frequency": 433775000,
  "modulation": "lora"
}
```

---

### Option 2: GNU Radio gr-lora_sdr (Comprehensive)

**Overview:** Use EPFL's `gr-lora_sdr` GNU Radio out-of-tree module, the most complete LoRa SDR implementation.

#### Pros
- ✅ **Most complete implementation** - Full LoRa PHY stack
- ✅ **Works at very low SNR** - Research-grade decoder
- ✅ **Well-documented** - Academic backing
- ✅ **Actively maintained** (2024)
- ✅ **Supports TX and RX**

#### Cons
- ❌ **Complex integration** - Requires GNU Radio runtime
- ❌ **Heavy dependencies** - GNU Radio + Python bindings
- ❌ **More resource-intensive**
- ❌ **Requires Python wrapper** to interface with OpenWebRX+

#### Integration Architecture

```
IQ Samples → GrLoRaSdrModule → GNU Radio Python → gr-lora_sdr blocks → Decoded packets → Parser
```

#### Implementation Details

Would require:
1. GNU Radio flowgraph wrapper script
2. Python bridge to execute GNU Radio in background
3. IPC mechanism (pipes/sockets) for data flow
4. Similar parser pattern as Option 1

**Estimated complexity:** ~300-500 lines of code

#### Installation Requirements

```bash
# Install GNU Radio
sudo apt install gnuradio

# Install gr-lora_sdr (conda method)
conda install -c conda-forge gr-lora_sdr

# Or build from source
git clone https://github.com/tapparelj/gr-lora_sdr
cd gr-lora_sdr
mkdir build && cd build
cmake ..
make && sudo make install
```

---

### Option 3: gr-lora (Original, Lighter)

**Overview:** Use rpp0's original `gr-lora` implementation, simpler than EPFL version.

#### Pros
- ✅ **Lighter than gr-lora_sdr**
- ✅ **Proven with RTL-SDR**
- ✅ **Good community support**
- ✅ **Documentation in English**

#### Cons
- ❌ Still requires GNU Radio
- ❌ Less feature-complete than gr-lora_sdr
- ❌ May not work at very low SNR
- ❌ Less actively maintained

#### Integration

Similar to Option 2 but with simpler GNU Radio flowgraph.

---

### Option 4: Pure Python Implementation (Custom)

**Overview:** Implement LoRa demodulator in pure Python using NumPy/SciPy.

#### Pros
- ✅ **No external binaries** - Pure Python
- ✅ **Full control** over demodulation
- ✅ **Easy to modify/extend**
- ✅ **Integrated debugging**

#### Cons
- ❌ **Most development work** - Must implement CSS demodulation from scratch
- ❌ **Performance concerns** - Python DSP is slower
- ❌ **Complex DSP math** - Chirp generation, dechirping, FFT, sync
- ❌ **Testing burden** - Must validate against real LoRa hardware

#### Implementation Outline

```python
class LoRaDemodulator:
    def __init__(self, bandwidth=125000, spreading_factor=7):
        self.bw = bandwidth
        self.sf = spreading_factor
        self.symbol_samples = (2 ** spreading_factor) * (sample_rate / bandwidth)

    def dechirp(self, iq_samples):
        """Multiply with base down-chirp"""
        # Generate down-chirp reference
        down_chirp = self._generate_chirp(direction="down")
        return iq_samples * down_chirp

    def detect_symbol(self, dechirped_samples):
        """FFT to detect symbol"""
        fft_result = np.fft.fft(dechirped_samples)
        symbol_index = np.argmax(np.abs(fft_result))
        return symbol_index

    def decode_packet(self, symbols):
        """Decode LoRa packet from symbols"""
        # Implement header parsing, payload extraction, CRC check
        pass
```

**Estimated complexity:** 1000+ lines for full implementation

#### References
- pyLoRa library (hardware interface, not demodulation)
- Academic papers on LoRa demodulation
- Existing GNU Radio implementations for reference

---

## Comparison Matrix

| Criterion | lorarx | gr-lora_sdr | gr-lora | Pure Python |
|-----------|--------|-------------|---------|-------------|
| **Complexity** | ⭐⭐⭐⭐⭐ Low | ⭐⭐ Medium | ⭐⭐⭐ Medium | ⭐ High |
| **Dependencies** | ⭐⭐⭐⭐ Light | ⭐ Heavy | ⭐⭐ Heavy | ⭐⭐⭐⭐⭐ None |
| **Performance** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good | ⭐⭐ Fair |
| **Features** | ⭐⭐⭐⭐ Complete | ⭐⭐⭐⭐⭐ Complete | ⭐⭐⭐ Good | ⭐ Basic |
| **Maintenance** | ⭐⭐⭐⭐ Easy | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐⭐ Easy |
| **Dev Time** | 1-2 days | 3-5 days | 3-5 days | 2-4 weeks |
| **Lines of Code** | ~100 | ~300-500 | ~300-500 | ~1000+ |

---

## Recommended Approach: Option 1 (lorarx)

### Rationale

1. **Follows established pattern:** Nearly identical to ISM/rtl_433 integration
2. **Minimal code changes:** ~100 lines across 6 files
3. **Feature complete:** Supports LoRaWAN, LoRa APRS, Meshcom, FANET
4. **Low risk:** Well-tested external tool
5. **Fast implementation:** 1-2 days for experienced developer

### Implementation Phases

#### Phase 1: Basic Integration (Day 1)
- [ ] Add mode definition to `owrx/modes.py`
- [ ] Add feature detection to `owrx/feature.py`
- [ ] Create `LoRaRxModule` in `csdr/module/toolbox.py`
- [ ] Create `LoRaDemodulator` in `csdr/chain/toolbox.py`
- [ ] Create `LoRaParser` in `owrx/toolbox.py`
- [ ] Add factory instantiation in `owrx/dsp.py`
- [ ] Test with lorarx binary installed

#### Phase 2: Testing & Refinement (Day 2)
- [ ] Test with real LoRa transmitters (LoRaWAN gateway, LoRa APRS)
- [ ] Verify JSON parsing for different packet types
- [ ] Add bookmarks for common LoRa frequencies
- [ ] Add configuration options (bandwidth, spreading factor)
- [ ] Documentation

#### Phase 3: Enhancement (Optional)
- [ ] Support multiple bandwidths/spreading factors simultaneously
- [ ] Add LoRaWAN packet decoding/display
- [ ] Integration with APRS map display for LoRa APRS
- [ ] Add signal quality metrics (SNR, RSSI)

### Sample Usage

Once implemented, users could:

1. **Navigate to LoRa APRS frequency:** 433.775 MHz (EU)
2. **Select mode:** "LoRa" from mode dropdown
3. **View decoded packets:** In message panel with colored sender IDs
4. **Background decoding:** Set as service for continuous monitoring

---

## Alternative Considerations

### When to use Option 2 (gr-lora_sdr)?

Consider if:
- Need best-in-class SNR performance
- Want to support LoRa transmission (future)
- Already have GNU Radio infrastructure
- Research/academic use case

### When to use Option 4 (Pure Python)?

Consider if:
- Cannot accept external dependencies
- Need deep integration with OpenWebRX+ DSP
- Want complete control over algorithm
- Have DSP expertise on team

---

## Configuration Schema

Proposed additions to OpenWebRX+ configuration:

```python
# In receiver settings
"lora_config": {
    "enabled": True,
    "bandwidths": [125000, 250000, 500000],  # Support multiple BW
    "spreading_factors": [7, 8, 9, 10, 11, 12],  # SF range
    "coding_rates": [5, 6, 7, 8],  # CR 4/5 to 4/8
    "implicit_header": False,
    "crc_check": True,
}
```

---

## Frequency Allocations

Common LoRa frequencies to include in bookmarks:

### Europe (868 MHz)
- 868.1 MHz - LoRaWAN uplink
- 868.3 MHz - LoRaWAN uplink
- 868.5 MHz - LoRaWAN uplink
- 433.775 MHz - LoRa APRS

### US (915 MHz)
- 903.9 MHz - 927.5 MHz - LoRaWAN channels (64 channels, 125 kHz)
- 927.9 MHz - LoRa APRS (proposed)

### Asia-Pacific
- 433 MHz - LoRa APRS
- 920-925 MHz - LoRaWAN (varies by country)

---

## Testing Strategy

### Unit Tests
- Parser JSON parsing with sample lorarx output
- Mode definition availability checks
- Feature detection logic

### Integration Tests
1. **LoRa APRS:** Use commercial LoRa APRS transmitter
2. **LoRaWAN:** Use TTN (The Things Network) gateway
3. **Meshtastic:** Use Meshtastic nodes
4. **SNR Testing:** Test at various signal levels

### Hardware Requirements
- RTL-SDR or similar (433/868/915 MHz capable)
- LoRa transmitter (Meshtastic, LoRa APRS tracker, or LoRaWAN node)

---

## Documentation Requirements

1. **Installation guide:** How to install lorarx binary
2. **Configuration guide:** Setting up LoRa frequencies
3. **Usage guide:** Decoding LoRaWAN, LoRa APRS, Meshtastic
4. **Troubleshooting:** Common issues and solutions
5. **Frequency reference:** LoRa band plans by region

---

## External Dependencies

### lorarx Binary
- **Source:** http://oe5dxl.hamspirit.at:8025/aprs/bin/
- **License:** TBD (need to verify)
- **Platforms:** Linux (x86_64, ARM)
- **Version:** Latest as of 2024

### Build Requirements (if building from source)
- C compiler (gcc/clang)
- Standard libraries
- May need sdrtst library

---

## Future Enhancements

1. **Multi-channel reception:** Decode multiple SF simultaneously
2. **LoRaWAN decryption:** With user-provided keys
3. **APRS-IS gateway:** Forward LoRa APRS to APRS-IS
4. **Meshtastic integration:** Display mesh network topology
5. **Transmission support:** Two-way communication (requires TX-capable SDR)
6. **Advanced analysis:** Packet statistics, network analysis, collision detection

---

## References

### Documentation
- [lorarx Wiki](https://dxlwiki.dl1nux.de/index.php?title=Lorarx)
- [gr-lora GitHub](https://github.com/rpp0/gr-lora)
- [gr-lora_sdr GitHub](https://github.com/tapparelj/gr-lora_sdr)
- [LoRa APRS](https://lora-aprs.info/)

### Academic Papers
- "From Demodulation to Decoding: Toward Complete LoRa PHY Understanding" (ACM TOSN)
- "Decoding LoRa: Realizing a Modern LPWAN with SDR" (GNU Radio Conference 2016)

### Community
- [RevSpace LoRa Decoding](https://revspace.nl/DecodingLora)
- [RTL-SDR Blog LoRa Decoding](https://www.rtl-sdr.com/tag/lora/)

---

## Conclusion

**Recommendation:** Implement Option 1 (lorarx) as the initial implementation due to:
- Low complexity and fast development
- Proven reliability
- Feature completeness
- Follows OpenWebRX+ architectural patterns

The design allows for future migration to other options if requirements change (e.g., moving to gr-lora_sdr for better performance or pure Python for deeper integration).

**Estimated total effort:** 2-3 days for complete implementation and testing.

---

## Appendix: Code Examples

### Complete lorarx Integration Example

See implementation details in each section above. Full working code would span:

1. `owrx/modes.py`: 1 line addition
2. `owrx/feature.py`: 1 line addition
3. `csdr/module/toolbox.py`: ~20 lines (LoRaRxModule class)
4. `csdr/chain/toolbox.py`: ~25 lines (LoRaDemodulator class)
5. `owrx/toolbox.py`: ~30 lines (LoRaParser class)
6. `owrx/dsp.py`: 3 lines (factory instantiation)

**Total:** ~80-100 lines of new code

### Sample lorarx Output (JSON)

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

This would be parsed and displayed in the OpenWebRX+ message panel with appropriate formatting and color coding.
