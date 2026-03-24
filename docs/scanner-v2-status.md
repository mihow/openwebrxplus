# Scanner V2 — Status Report

> Updated: 2026-03-24 21:10 PDT

## Summary

Signal-driven radio scanner built as an OpenWebRX+ fork extension. Sweeps 25-1700 MHz, detects signals via FFT, classifies by mode, logs to SQLite, and serves a mobile-first web UI.

**Branch:** `feat/scanner-v2` — 35 commits, 91 tests
**PRs:** [pi-sdr#3](https://github.com/mihow/pi-sdr/pull/3) (design) | [openwebrxplus#11](https://github.com/mihow/openwebrxplus/pull/11) (implementation)

## What works

### Fully working
- **Signal detection** from IQ files: FFT peak finding, noise floor tracking, signal merging
- **Classification pipeline**: frequency-band mode detection (AM/NFM/WFM), pluggable content filters
- **SQLite logging**: detections, bookmarks, scan sessions — queryable
- **CLI tools**: `scan_iq.py` (scan IQ files → WAV), `analyze_scan.py` (audit results), `record_bands.sh` (capture from SDRplay)
- **Offline demod**: FM/AM/NFM demodulation from IQ files with de-emphasis, produces listenable WAV (confirmed: Mount Scott repeater 443.150 MHz, NOAA WX7 162.550 MHz)
- **Known frequency database**: Portland FM, NOAA, air band, marine, ham, GMRS — labels detections
- **Mobile UI structure**: activity feed, listening view, log view, settings — all render correctly
- **Test tone**: 440 Hz plays on phone (confirms Web Audio API works on mobile)
- **Live scanning**: scanner sweeps spectrum, detects signals, populates UI in real-time
- **WebSocket handshake**: scanner UI correctly handshakes with OpenWebRX+ and subscribes to state

### Partially working
- **Live audio**: DSP chain code exists (`_ensureScannerDsp`, `_tuneScannerDsp`), WebSocket routes commands, but audio binary messages (0x02) are not flowing to the client. Root cause under investigation.
- **Recording playback in UI**: endpoint exists (`/api/scanner/recordings/{id}`), JS playback code exists, but untested end-to-end with real recordings in the DB.
- **SDR retune on hold**: code added to retune SDR when user taps a frequency, but offset tuning (avoiding DC spike) not implemented.

### Not working / not started
- **Real-time audio on mobile**: blocked by DSP chain issue above
- **Opus recording service**: `recorder.py` exists but not wired into live scan loop
- **Tailscale HTTPS**: needs sudo for `tailscale serve`, HTTP works on LAN
- **Background scanning**: scanner runs when UI is open but doesn't persist as a service

## Known bugs

| Bug | Severity | Status |
|-----|----------|--------|
| DSP chain doesn't produce 0x02 audio messages | **High** | Investigating — may be missing `dspcontrol {action: "start"}` message |
| SQLite "cannot start transaction within transaction" | Medium | Fix committed (isolation_level=None), needs verification |
| Dead WebSocket listeners cause "fd=-1" errors | Medium | Fix needed in connection cleanup |
| offset_freq must be int, was float | Medium | Fix committed (cast to int) |
| DC spike at center freq degrades audio | Medium | Need offset tuning (retune ±100 kHz) |
| SDRplay hwVer=255 (API version mismatch?) | Low | Works despite warning, may affect some features |

## Architecture

```
Mobile UI (/scanner)          Standard UI (/)
     │                              │
     └── WebSocket (/ws/) ──────────┘
              │
     OpenWebRxReceiverClient
     ├── scanner_subscribe → ScannerState listener
     ├── scanner_command → ScannerService
     └── DspManager → ClientDemodulatorChain → audio (0x02)
              │
     ScannerService (background thread)
     ├── FrequencySweeper (window management)
     ├── SdrBridge → FftChain → FFT power data
     ├── SignalDetector (peak finding)
     ├── ClassificationPipeline (mode ID)
     └── ScannerDatabase (SQLite)
```

## File inventory

### Scanner modules (`owrx/scanner/`)
| File | Lines | Tests | Purpose |
|------|-------|-------|---------|
| `__init__.py` | ~280 | 5 | ScannerService, ScannerState |
| `detector.py` | ~100 | 11 | FFT peak finding, noise floor |
| `sweep.py` | ~80 | 9 | Frequency windows, band→mode |
| `classifier.py` | ~80 | 10 | Pluggable classification |
| `db.py` | ~170 | 8 | SQLite schema + queries |
| `known_freqs.py` | ~90 | 20 | Portland frequency database |
| `recorder.py` | ~120 | ? | Opus recording (untested live) |
| `sdr_bridge.py` | ~80 | 0 | FftChain bridge to SdrSource |
| `config.py` | ~20 | 0 | Config key documentation |

### Integration points (modified OWRX+ files)
| File | Changes | Purpose |
|------|---------|---------|
| `owrx/http.py` | +7 routes | Scanner REST API |
| `owrx/connection.py` | +120 lines | WebSocket scanner handling, DSP chain |
| `owrx/config/defaults.py` | +14 keys | Scanner config defaults |
| `owrx/controllers/scanner.py` | new, ~170 lines | REST controllers |

### Frontend (`htdocs/scanner/`)
| File | Purpose |
|------|---------|
| `scanner.html` | Page shell |
| `app.js` | WebSocket, state, commands |
| `audio.js` | ADPCM decode, Web Audio, test tone, recording playback |
| `views.js` | Activity feed, listening, log, settings views |
| `scanner.css` | Mobile-first styles |
| `scanner-audio-processor.js` | AudioWorklet processor |

### CLI tools (`scripts/`)
| Script | Purpose |
|--------|---------|
| `scan_iq.py` | Scan IQ files: detect → classify → log → demod → WAV |
| `analyze_scan.py` | Audit detections, audio quality, mode mismatches |
| `record_bands.sh` | Record IQ from SDRplay across all voice bands |

### Tests (`test/scanner/`)
91 tests total across: test_db.py, test_detector.py, test_detector_real_iq.py, test_sweep.py, test_classifier.py, test_known_freqs.py, test_scanner_service.py, test_e2e_scanner.py

## Priority TODO

### P0 — Get audio working
1. **Trace exact WebSocket message sequence** that standard OpenWebRX+ client uses for audio (research agent running)
2. **Fix DSP chain startup** — scanner client may be missing `dspcontrol {action: "start"}` or `connectionproperties`
3. **Implement offset tuning** — retune SDR ±100 kHz from target, use offset_freq in DSP

### P1 — Offline recording + playback (doesn't need live audio)
4. **Wire recorder into scan loop** — when scanner detects a signal, record the audio
5. **Test recording playback in UI** — verify `/api/scanner/recordings/{id}` → browser play
6. **Populate DB from IQ file scanning** — `scan_iq.py` should save WAV recordings and set recording_path in DB

### P2 — Dev process
7. **Enable hot-reload** for Python changes in Docker (avoid full restart)
8. **Add WebSocket protocol test** — automated test that opens WS, sends handshake, verifies audio flow
9. **Fix stale WebSocket listeners** — clean up on disconnect
10. **Fix sdrplay daemon management** — single source of truth, no host/container conflicts

### P3 — Features
11. Add Portland repeater frequencies to known_freqs.py
12. Mobile HTTPS via Tailscale serve
13. Background scanning as persistent service
14. VAD (voice activity detection) for content filtering

## Hardware notes
- SDRplay RSP1a on Beast, serial 19030F2B96
- `sdrplay_apiService` must be single instance — host service is now masked via systemd
- Docker container (`scanner-dev`) is privileged with USB passthrough
- rx_sdr built at `/tmp/rx_tools/build/rx_sdr`
- Container image: `slechev/openwebrxplus-softmbe:latest` (amd64)
