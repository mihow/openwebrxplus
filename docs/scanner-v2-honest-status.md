# Scanner V2 — Honest Status

> 2026-03-24, end of 3-day sprint

## What we built

A signal-driven radio scanner as an OpenWebRX+ extension. It sweeps 25-960 MHz via an SDRplay RSP1a, detects signals by FFT peak-finding, classifies by frequency band, logs to SQLite, and serves a mobile-first web UI.

## What actually works (verified in browser)

- **Live scanning**: sweeps spectrum, detects signals, shows them in real-time UI
- **Live audio**: hold on a frequency → ADPCM audio streams over WebSocket → plays in browser. Confirmed working on NOAA 162.55 MHz and FM 91.5/97.1 MHz
- **Offset tuning**: SDR retunes 100 kHz below signal to avoid DC spike
- **Auto-hold recording**: scanner detects strong signal → auto-holds for 5s → DSP chain records real demodulated audio → resumes scanning
- **Recording playback**: log view shows play buttons, click to play recordings in browser
- **Debug page**: WebSocket inspector showing message flow, audio pipeline status, waveform visualization, detection list with playback

## What doesn't work / is broken

- **Scan speed**: sweeps in 2.4 MHz windows. The SDRplay RSP1a supports up to 10 MHz. Covering 25-960 MHz in 2.4 MHz steps = 390 windows × 0.5s dwell + 5s auto-listen per signal = takes forever. Should use 8-10 MHz windows.
- **Marker tones during sweep**: detections logged during the fast sweep have no recordings (we removed marker tones). Only auto-hold detections get real audio. The log is full of entries with no play button.
- **No squelch / signal persistence**: scanner doesn't know if a signal is still active. It detects a peak in the FFT, logs it, maybe auto-holds, then moves on. A real scanner would track signals across dwells.
- **Reconnection**: refreshing the browser page loses audio state. The "tap to start" overlay is required every time.
- **Double recordings/ path**: storage path nesting bug
- **S-meter near zero**: reading not calibrated for SDRplay

## Architecture

```
Browser (scanner-debug.html)
  ↕ WebSocket (ws://)
  ↕ JSON state + binary 0x02 ADPCM audio

OpenWebRX+ Server
  ├── ScannerService (scan loop thread)
  │   ├── FrequencySweeper (2.4 MHz windows, should be 8-10 MHz)
  │   ├── SdrBridge → FftChain → FFT power spectrum
  │   ├── SignalDetector (peak finding, noise floor tracking)
  │   ├── ClassificationPipeline (freq band → mode)
  │   ├── Auto-hold (strongest signal → LISTENING state)
  │   └── ScannerDatabase (SQLite)
  │
  ├── connection.py (scanner WebSocket integration)
  │   ├── _tuneScannerDsp() → DspManager → demodulated audio
  │   ├── _startScannerRecording() → ADPCM decode → ScannerRecorder
  │   └── write_dsp_data() → 0x02 frame to browser + recorder tap
  │
  └── ScannerRecorder (WAV/Opus file output)

SDRplay RSP1a (USB, up to 10 MHz bandwidth)
```

## File inventory

### Python (owrx/scanner/)
| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~400 | ScannerService, ScannerState, auto-hold |
| `detector.py` | ~100 | FFT peak finding |
| `sweep.py` | ~80 | Frequency window management |
| `classifier.py` | ~80 | Signal classification |
| `db.py` | ~170 | SQLite schema + queries |
| `known_freqs.py` | ~90 | Portland frequency database |
| `recorder.py` | ~120 | WAV/Opus recording |
| `adpcm.py` | ~90 | ADPCM decoder for DSP tap |
| `dsp.py` | ~75 | FM/AM demod (scipy) |
| `sdr_bridge.py` | ~80 | OpenWebRX+ SDR integration |

### Frontend (htdocs/scanner/)
| File | Purpose |
|------|---------|
| `scanner.html` | Mobile scanner UI |
| `app.js` | WebSocket, state, commands |
| `audio.js` | ADPCM decode, Web Audio, playback |
| `views.js` | Activity feed, listening, log, settings |
| `scanner.css` | Mobile-first styles |
| `scanner-debug.html` | Debug/dev page with WS inspector |

### Tests: 107 passing

## What's wrong with the approach

1. **Too much infrastructure, not enough product.** 3 days of work produced 107 tests, a plan document, status docs, and careful architecture — but the actual scanner barely works. Should have spent day 1 getting a single frequency recording working end-to-end, then iterated.

2. **Building inside OpenWebRX+ is heavy.** Every change requires restarting a Docker container. The WebSocket protocol is complex. The DSP chain is a black box. A standalone Python script with a web UI (Flask + WebSocket) would have been faster to iterate on.

3. **2.4 MHz scan windows are too narrow.** The SDRplay supports 10 MHz. Even the RTL-SDR V4 does 2.4 MHz, but the RSP1a should use its full bandwidth. The FrequencySweeper needs to support variable window sizes based on hardware capability.

4. **No signal tracking.** Real scanners track signals across time — they know "this frequency has been active for 30 seconds" vs "this was a one-time blip." Our scanner just logs instantaneous FFT peaks.

## Next priorities (if continuing)

1. **Increase scan bandwidth to 8-10 MHz** — one config change in FrequencySweeper + SdrBridge
2. **Fix recording during sweep** — either bring back marker tones or make auto-hold record to the same DB row as the detection
3. **Add signal persistence** — track signals across dwells, only auto-hold on signals that persist for N dwells
4. **Look at RTLSDR-Airband** — it solves the same problem (FFT channelizer + squelch-triggered recording) and is production-ready on Pi

## Research conclusions

- **GNU Radio**: good future path for P25/DMR/LoRa modes. `apt install gnuradio` on Trixie. Not needed for current FM/AM MVP.
- **RTLSDR-Airband**: FFT channelizer + multi-channel recording, runs on Pi. Worth evaluating as an alternative backend.
- **Playwright**: highest-value testing addition for browser e2e tests.
- **Code quality**: needs ruff, CI, pyright. ~30 min to set up.

## Commits this sprint (14)

```
c78cbfd2 feat: auto-hold on strong signals to record real audio
b4fe98c3 fix: re-enable marker tone recordings during scan sweep
f52b6c23 feat: add auto-refreshing detections panel to debug page
209a7006 feat: record real demodulated audio from DSP chain
861e2357 fix: add freq input, change hold to 91.5, filter noisy WS messages
4da4c993 feat: add scanner audio debug page with WebSocket inspector
de5023d1 fix: pull scanner_storage_path from OWRX+ config, use persistent DB
d48aea51 fix: cast offset_freq to int in dspcontrol handler
0b4e3b50 docs: update scanner v2 status after recorder + offset tuning work
41081084 feat: implement offset tuning to avoid DC spike at center frequency
90320f0e test: add offset tuning calculation tests (red)
d4a030d8 test: add scan loop recorder integration tests (red)
+ 2 earlier commits (DSP consolidation, ADPCM SYNC fix)
```
