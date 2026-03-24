OpenWebRX+
=========

This is the **improved version** of the OpenWebRX online SDR. The pre-built OpenWebRX+ packages are available from the [package repository](https://luarvique.github.io/ppa/). Pre-built disk images are available from the [Releases page](https://github.com/luarvique/openwebrx/releases). OpenWebRX+ [documentation](https://fms.komkon.org/OWRX/) draft is now available. News, support, and general discussion can be found in the [Telegram channel](https://t.me/openwebrx) and related [chat](https://t.me/openwebrx_chat). Features found in OpenWebRX+ that are not present in the original version:
* AIS, SSTV, FAX, FLEX, POCSAG, HFDL, VDL2, ADSB, ACARS, ISM, RDS, SAM, SITOR-B, RTTY, and CW decoders.
* DTMF, EEA, EIA, CCIR, and several ZVEY SELCALL decoders.
* Background SSTV and FAX decoding with received images browser.
* Built-in chat between receiver users.
* Built-in recorder for received audio.
* Built-in scanner over bookmarks.
* Ability for the admin to see user connections and ban abusive users.
* Adjustable noise filtering based on spectral subtraction.
* Adjustable tuning step.
* Automatically created bookmarks for shortwave broadcasts.
* Automatically created bookmarks for nearby HAM repeaters.
* Waterfall panning and zooming on touchscreen based devices.
* Bandpass control with the scroll wheel.
* Improved tuning in CW mode.
* More reliable SDRPlay devices operation.
* Map shows other public web SDRs from all around the world.
* Map shows shortwave broadcasters from all around the world.
* Map shows aircraft positions received over ADSB, VDL2, HFDL.
* Map shows nearby HAM repeaters.
* Better map information, with distances, APRS paths, weather, etc.
* Support for configurable session timeout, with a policy page.
* HTTPS protocol support (requires certificate).
* Foldable receiver panel with configurable opacity.
* Spectrum display.

Original OpenWebRX
=========

OpenWebRX is a multi-user SDR receiver software with a web interface.

![OpenWebRX](https://www.openwebrx.de/gfx/openwebrx-screenshot.png)

It has the following features:

- [csdr](https://github.com/jketterl/csdr) based demodulators (AM/FM/SSB/CW/BPSK31/BPSK63)
- filter passband can be set from GUI
- it extensively uses HTML5 features like WebSocket, Web Audio API, and Canvas
- it works in Google Chrome, Chromium and Mozilla Firefox
- supports a wide range of [SDR hardware](https://github.com/jketterl/openwebrx/wiki/Supported-Hardware#sdr-devices)
- Multiple SDR devices can be used simultaneously
- [digiham](https://github.com/jketterl/digiham) based demodularors (DMR, YSF, Pocsag, D-Star, NXDN)
- [wsjt-x](https://wsjt.sourceforge.io/) based demodulators (FT8, FT4, WSPR, JT65, JT9, FST4,
  FST4W)
- [direwolf](https://github.com/wb2osz/direwolf) based demodulation of APRS packets
- [JS8Call](http://js8call.com/) support
- [DRM](https://github.com/jketterl/openwebrx/wiki/DRM-demodulator-notes) support
- [FreeDV](https://github.com/jketterl/openwebrx/wiki/FreeDV-demodulator-notes) support
- M17 support based on [m17-cxx-demod](https://github.com/mobilinkd/m17-cxx-demod)

## Setup

The following methods of setting up a receiver are currently available:

- Raspberry Pi SD card images
- Debian repository
- Docker images
- Manual installation

Please checkout the [setup guide on the wiki](https://github.com/jketterl/openwebrx/wiki/Setup-Guide) for more details
on the respective methods.

## Community

If you have trouble setting up or configuring your receiver, you have some great idea you want to see implemented, or
you just generally want to have some OpenWebRX-related chat, come visit us over on
[our groups.io group](https://groups.io/g/openwebrx).

If you want to hang out, chat, or get in touch directly with the developers, receiver operators or users, feel free to
drop by in [our Discord server](https://discord.gg/gnE9hPz).

## Usage tips

You can zoom the waterfall display by the mouse wheel. You can also drag the waterfall to pan across it.

The filter envelope can be dragged at its ends and moved around to set the passband.

However, if you hold down the shift key, you can drag the center line (BFO) or the whole passband (PBS).

## Licensing

---

## Scanner V2 Development Guide

This fork adds a signal-driven radio scanner that sweeps the full SDR range, detects signals via FFT, classifies them, and logs everything to SQLite. See the [design spec](https://github.com/mihow/pi-sdr/pull/3) for full details.

### Quick start

```bash
# Build rx_sdr for IQ recording (one-time)
cd /tmp && git clone https://github.com/rxseger/rx_tools.git
cd rx_tools && mkdir build && cd build && cmake .. && make

# Record IQ files from SDRplay RSP1a
cd /path/to/openwebrx+
./scripts/record_bands.sh                     # all bands
./scripts/record_bands.sh --band noaa         # just NOAA weather
./scripts/record_bands.sh --band 70cm --duration 30

# Scan IQ files (detect, classify, demod, save WAV)
python3 scripts/scan_iq.py test_data/iq/*.cf32
python3 scripts/scan_iq.py test_data/iq/file.cf32 --demod-all
python3 scripts/scan_iq.py test_data/iq/file.cf32 --demod-freq 162550000

# Analyze results
python3 scripts/analyze_scan.py
python3 scripts/analyze_scan.py --issues-only
python3 scripts/analyze_scan.py --csv detections.csv

# Run tests
python3 -m pytest test/scanner/ -v
```

### Scanner modules

| Module | Purpose |
|--------|---------|
| `owrx/scanner/detector.py` | FFT peak finding, noise floor tracking, signal merging |
| `owrx/scanner/sweep.py` | Frequency window management, band-to-mode mapping |
| `owrx/scanner/classifier.py` | Pluggable classification pipeline (mode, content filter, action) |
| `owrx/scanner/db.py` | SQLite database for detections, bookmarks, sessions |
| `owrx/scanner/known_freqs.py` | Known frequency database (Portland area) |
| `owrx/scanner/config.py` | Scanner config key documentation |
| `owrx/scanner/__init__.py` | ScannerService: background scan loop, state management |
| `owrx/controllers/scanner.py` | REST API: `/api/scanner`, `/api/scanner/detections`, etc. |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/record_bands.sh` | Record IQ files from SDRplay across FM, NOAA, air, ham, GMRS, marine, HF |
| `scripts/scan_iq.py` | Scan IQ files: detect → classify → log → demod → WAV |
| `scripts/analyze_scan.py` | Audit scan results: mode mismatches, audio quality, duplicates |

### SDRplay RSP1a notes

- Use 6 MHz max sample rate for 14-bit ADC (>6 MHz drops to 12-bit, >8 MHz to 10-bit)
- `sdrplay_apiService` must be running (only one instance, kill duplicates)
- Gain is inverted: IFGR 20 = max gain, IFGR 59 = min gain
- FM notch and DAB notch filters available in hardware
- Docker needs `privileged: true` for USB re-enumeration

---

OpenWebRX is available under Affero GPL v3 license
([summary](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0))).

OpenWebRX is also available under a commercial license on request. Please contact me at the address
*&lt;randras@sdr.hu&gt;* for licensing options. 
