Continue scanner v2 on the OpenWebRX+ fork (`~/Projects/Radio/OpenWebRX/openwebrx+` branch `feat/scanner-v2`). Read the honest status at `docs/scanner-v2-honest-status.md` and this prompt for full context.

## Where we left off (2026-03-24)

The scanner "works" but barely qualifies as MVP. After 3 days of work we have a lot of infrastructure but the core experience is poor: the scanner mostly stops on static/noise, rarely lands on actual voice signals. The signal detection is too sensitive (SNR threshold 10-15 dB catches everything) and there's no signal persistence tracking — it treats every FFT peak as worth recording.

## What works
- Live scanning: sweeps 25-960 MHz in 8 MHz windows via SDRplay RSP1a
- Live audio: ADPCM over WebSocket plays in browser when holding on a frequency
- Auto-hold: locks on strongest signal (>15dB SNR) for 5s, records via DSP chain tap
- Recording: real demodulated audio saved as WAV via ADPCM decoder + ScannerRecorder
- Debug page: `http://localhost:8073/static/scanner-debug.html` — sortable detections table, WS inspector, waveform, audio pipeline status
- Offset tuning: SDR retunes 100kHz below signal to avoid DC spike
- Resume: stop/start preserves scan position
- Mute: gain-based toggle (not audioCtx.suspend)
- Squelch: closed during scanning, open only during listening

## What's broken / bad
- **Stops on static more than signals** — SNR threshold too low, no signal persistence, no voice activity detection. Most auto-holds are on noise peaks or broadband interference, not actual transmissions.
- **Recordings are mostly static** — because auto-hold fires on noise. Need squelch or VAD.
- **No signal tracking across dwells** — a signal detected once is treated the same as one detected 10 times. Real scanners require signals to persist across multiple dwells before locking on.
- **WFM recordings are 44 bytes (header only)** — DSP chain takes time to retune for wideband FM, recording starts before audio flows. AM recordings work (460KB+).
- **Two state listeners per connection** — if two browser tabs are open, both try to control recording. Mostly fixed by moving recording to singleton, but `_onScannerStateChange` still fires per-connection.

## Architecture notes
- Scanner runs inside OpenWebRX+ Docker container (`scanner-dev`), source mounted as volumes
- Python changes need container restart; JS changes are instant with browser refresh
- ScannerService is singleton, scan loop runs in background thread
- Recording: ScannerService._start_recording() → ADPCM decoder → ScannerRecorder (WAV/Opus)
- Audio to browser: DSP chain → write_dsp_data() → 0x02 WebSocket frame → ADPCM decode in JS → Web Audio API
- Config from OWRX+ defaults.py: scanner_storage_path=/var/lib/openwebrx/recordings
- SDR profile in /var/lib/openwebrx/settings.json: samp_rate=8000000

## Key files
- `owrx/scanner/__init__.py` — ScannerService, scan loop, auto-hold, recording
- `owrx/scanner/adpcm.py` — ADPCM decoder for DSP tap recording
- `owrx/scanner/detector.py` — FFT signal detection
- `owrx/scanner/recorder.py` — WAV/Opus file recording
- `owrx/connection.py:590-720` — WebSocket scanner integration, DSP chain control
- `htdocs/scanner-debug.html` — debug/dev UI (the one that actually works)
- `htdocs/scanner/` — original mobile UI (less useful than debug page)

## Honest assessment

We are in over our heads building a scanner from scratch inside OpenWebRX+. The core problem — reliably distinguishing real voice signals from noise/interference — is hard and well-solved by existing tools (trunk-recorder, RTLSDR-Airband). Our FFT peak detector with a simple SNR threshold is not good enough.

Options for next session:
1. **Improve signal detection** — add persistence (require signal detected N times before auto-hold), raise SNR threshold, add squelch timeout, maybe simple VAD
2. **Use RTLSDR-Airband as backend** — it has a production-ready FFT channelizer + squelch-triggered recording. We could use it for scan/detect/record and keep our web UI for playback.
3. **Add GNU Radio** — `apt install gnuradio` on Trixie, use proper DSP blocks for signal detection. Future path for P25/DMR/LoRa.
4. **Simplify scope** — instead of scanning 25-960 MHz, focus on known active frequency ranges (Portland public safety, NOAA, FM broadcast, aviation) with hardcoded bookmarks and just cycle through those.

Option 4 is probably the fastest to a useful tool.

## Research from this session
- GNU Radio: available on Trixie arm64, good for future modes (P25/DMR), overkill for current FM/AM
- RTLSDR-Airband: solves our exact problem, runs on Pi, worth evaluating
- Code review: needs ruff, CI, Playwright tests. ~30 min to set up basics.
- React+TypeScript: recommended for next UI iteration

## Test suite
107 tests passing. Run: `cd ~/Projects/Radio/OpenWebRX/openwebrx+ && python3 -m pytest test/scanner/ -v`
