# LoRa Support Design Documentation

This directory contains comprehensive design documentation for adding LoRa (Long Range) support to OpenWebRX+.

## Documents Overview

### 📘 [lora-implementation-design.md](lora-implementation-design.md)
**Main design document** with detailed analysis of four implementation approaches.

**Contents:**
- Executive summary and background
- **Licensing & open source status** - Clarifies what's proprietary vs. open
- Four implementation options with pros/cons
- Complete code examples for recommended approach (lorarx)
- Configuration schemas and frequency allocations
- Testing strategy and future enhancements

**Key Section:** [LoRa Licensing & Open Source Status](lora-implementation-design.md#lora-licensing--open-source-status) - Essential reading to understand the legal landscape.

---

### 🚀 [lora-quick-start-guide.md](lora-quick-start-guide.md)
**Practical implementation guide** for the recommended approach (lorarx).

**Contents:**
- Step-by-step implementation instructions
- Complete code templates for all 6 files (~100 lines total)
- Installation and prerequisites
- Testing procedures and troubleshooting
- Git commit strategy
- Success criteria and timeline (2-3 days)

**Use this for:** Actually implementing LoRa support following the recommended approach.

---

### 📊 [lora-comparison.md](lora-comparison.md)
**Visual comparison** of all four implementation options.

**Contents:**
- Architecture diagrams for each approach
- Feature comparison matrices
- Performance benchmarks (CPU, memory, latency)
- Code complexity comparison (100 vs 400 vs 1000+ LOC)
- Risk assessment
- Installation complexity
- Decision matrix and use case recommendations

**Use this for:** Understanding trade-offs between different approaches and making informed decisions.

---

## Quick Summary

### The Question: "Is LoRa proprietary with no licensed software available?"

**Answer:** **NO, this is misleading.** Here's the reality:

#### What's Proprietary ⚠️
- **LoRa Physical Layer (CSS modulation):** Patented by Semtech
- **Official Semtech chipsets:** Required for certified hardware

#### What's Open ✅
- **LoRaWAN Protocol:** Open standard (LoRa Alliance), ITU-approved
- **LoRaWAN Specifications:** Freely available, no licensing fees
- **Open-source decoders:** Multiple implementations exist
  - lorarx (OE5DXL) - Standalone binary
  - gr-lora_sdr (EPFL) - GNU Radio blocks, GPL-3.0
  - gr-lora (rpp0) - GNU Radio blocks, GPL-3.0
  - IBM's LoRaWAN in C - Eclipse Public License

#### Legal Status 📜
- Open-source implementations are **reverse-engineered**
- Semtech holds patents but **has not sued open-source projects**
- **Non-commercial use** (amateur radio, research) is generally tolerated
- **OpenWebRX+ is well-positioned:** Non-commercial, receive-only, educational

**Bottom line:** Multiple open-source LoRa decoders exist and are widely used. OpenWebRX+ can safely implement LoRa support using these tools.

---

## Recommended Implementation: lorarx

**Why lorarx?**
- ⭐ Simplest integration (~100 lines across 6 files)
- ⭐ Follows existing OpenWebRX+ patterns (ISM/rtl_433)
- ⭐ Feature-complete (LoRaWAN, LoRa APRS, Meshtastic, FANET)
- ⭐ Fast implementation (2-3 days)
- ⭐ Low maintenance burden
- ⭐ Aligns with CLAUDE.md principles (use existing tools)

**Architecture:**
```
IQ Samples → LoRaRxModule → lorarx binary → JSON → Parser → WebSocket
```

**Files to modify:**
1. `owrx/modes.py` (1 line)
2. `owrx/feature.py` (1 line)
3. `csdr/module/toolbox.py` (~25 lines)
4. `csdr/chain/toolbox.py` (~30 lines)
5. `owrx/toolbox.py` (~35 lines)
6. `owrx/dsp.py` (3 lines)

**Total: ~100 lines of code**

---

## Alternative Approaches

### Option 2: gr-lora_sdr (GNU Radio + EPFL implementation)
- **Best-in-class SNR performance**
- **Full LoRa PHY stack**
- More complex (~400 lines, 1-2 weeks)
- Heavy dependencies (GNU Radio)

### Option 3: gr-lora (Original GNU Radio implementation)
- Lighter than gr-lora_sdr
- Good community support
- Similar complexity (~400 lines, 1-2 weeks)

### Option 4: Pure Python (Custom implementation)
- No external dependencies
- Full control over algorithm
- Most complex (~1000+ lines, 3-4 weeks)
- Significant DSP expertise required

---

## Implementation Timeline

### Recommended (lorarx): 2-3 days
- **Day 1:** Basic integration (6 files, ~100 lines)
- **Day 2:** Testing with real LoRa hardware
- **Day 3:** Documentation and refinement

### Alternative (gr-lora_sdr): 1-2 weeks
- Week 1: GNU Radio wrapper, integration, testing
- Week 2: Debugging and optimization

### Custom (Pure Python): 3-4 weeks
- Week 1: Design and chirp generation
- Week 2: Demodulation and synchronization
- Week 3: Decoding and CRC
- Week 4: Testing and validation

---

## Supported LoRa Applications

Once implemented, OpenWebRX+ will decode:

### LoRaWAN
- IoT sensor networks
- The Things Network (TTN) devices
- Smart city infrastructure

### LoRa APRS
- Position tracking
- Telemetry data
- Amateur radio messaging

### Meshtastic
- Off-grid messaging
- Mesh network topology
- Hiking/outdoor communication

### FANET (Flight Area Network)
- Paragliders and hang gliders
- Aircraft tracking
- Flight data

---

## Frequency Bands

### Europe
- 433.775 MHz - LoRa APRS
- 868.1/868.3/868.5 MHz - LoRaWAN

### United States
- 903.9 - 927.5 MHz - LoRaWAN (64 channels)
- 927.9 MHz - LoRa APRS (proposed)

### Asia-Pacific
- 433 MHz - LoRa APRS
- 920-925 MHz - LoRaWAN (varies by country)

---

## Next Steps

1. **Read the licensing section** in [lora-implementation-design.md](lora-implementation-design.md#lora-licensing--open-source-status)
2. **Review the comparison** in [lora-comparison.md](lora-comparison.md) to understand options
3. **Follow the quick start guide** in [lora-quick-start-guide.md](lora-quick-start-guide.md) to implement
4. **Install lorarx binary** from http://oe5dxl.hamspirit.at:8025/aprs/bin/
5. **Test with real LoRa hardware** (LoRa APRS, LoRaWAN, Meshtastic)

---

## References

### Specifications
- LoRa Alliance: https://lora-alliance.org/
- LoRaWAN Specification: https://lora-alliance.org/resource_hub/
- ITU-T Y.4480 (LoRaWAN as LPWAN standard)

### Open Source Implementations
- lorarx: http://oe5dxl.hamspirit.at:8025/aprs/bin/
- gr-lora_sdr: https://github.com/tapparelj/gr-lora_sdr
- gr-lora: https://github.com/rpp0/gr-lora

### Patents & Legal
- Semtech LoRa Patents: US Patent #20160094269A1
- Academic Research: "From Demodulation to Decoding: Toward Complete LoRa PHY Understanding" (ACM TOSN)

### Communities
- LoRa APRS: https://lora-aprs.info/
- Meshtastic: https://meshtastic.org/
- The Things Network: https://www.thethingsnetwork.org/

---

## Contributing

This design is based on OpenWebRX+ architecture patterns and the CLAUDE.md development guidelines. When implementing:

1. Follow existing decoder patterns (ISM, PAGE, APRS)
2. Minimize external dependencies
3. Use command-line tools where possible
4. Keep code simple and maintainable
5. Document thoroughly

See [CLAUDE.md](../../CLAUDE.md) for full development guidelines.

---

## Questions?

- **Licensing concerns?** See the [licensing section](lora-implementation-design.md#lora-licensing--open-source-status)
- **Which approach?** See the [comparison document](lora-comparison.md)
- **How to implement?** See the [quick start guide](lora-quick-start-guide.md)
- **Technical details?** See the [implementation design](lora-implementation-design.md)

---

**Last Updated:** 2025-11-19
**Status:** Design Phase - Ready for Implementation
