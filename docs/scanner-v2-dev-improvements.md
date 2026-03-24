# Scanner V2 — Development Process Improvements

> From code review session 2026-03-24. These are concrete next steps to improve testability, iteration speed, and independence from hardware.

## Top 3 Priorities

### 1. Consolidate DSP functions into `owrx/scanner/dsp.py`

`extract_channel()`, `demod_fm()`, `demod_am()`, `save_wav()` are duplicated in `test_e2e_scanner.py` and `scripts/scan_iq.py` with slightly different implementations. Move to a shared module.

This also makes the demod logic available for the recorder to use when saving audio from live scanning.

### 2. Test scan loop with synthetic FFT data (no hardware needed)

```python
def test_scan_loop_detects_signal():
    svc = ScannerService()
    fft_data = np.full(1024, -90.0, dtype=np.float32)
    fft_data[500:520] = -50.0  # signal

    frames = iter([fft_data, fft_data, None])
    svc.start(
        config={"freq_start": 100e6, "freq_stop": 200e6,
                "dwell_time": 0.01, "db_path": ":memory:"},
        retune_callback=lambda f: None,
        fft_callback=lambda: next(frames),
    )
    time.sleep(0.5)
    svc.stop()
    assert svc.db.get_recent_detections(limit=10)
```

This tests sweeper → detector → classifier → DB integration without SDR or OpenWebRX+.

### 3. Generate small synthetic IQ fixtures for CI

Commit small (100 KB) IQ files with known injected signals. Run e2e tests in CI without real SDR recordings.

## Additional Improvements

### Extract scanner audio routing from connection.py

The `_ensureScannerDsp`, `_tuneScannerDsp`, `_onScannerStateChange` code in `owrx/connection.py:580-700` mixes WebSocket transport with audio routing. Extract to `ScannerAudioRouter` class that takes a DspManager reference.

### WebSocket protocol test (Python, no browser)

```python
# Test with websockets library
async def test_scanner_audio_flow():
    ws = await websockets.connect("ws://localhost:8073/ws/")
    await ws.send("SERVER DE CLIENT client=test type=receiver")
    response = await ws.recv()  # "CLIENT DE SERVER..."
    await ws.send(json.dumps({"type": "scanner_subscribe"}))
    await ws.send(json.dumps({"type": "scanner_command", "command": "start"}))
    # Wait for binary audio frame
    msg = await asyncio.wait_for(ws.recv(), timeout=30)
    assert isinstance(msg, bytes) and msg[0] == 0x02
```

### Fix singleton for testing

```python
@classmethod
def get_instance(cls, reset=False):
    if reset or cls._instance is None:
        cls._instance = cls()
    return cls._instance
```

### Hot-reload for frontend dev

Set `Cache-Control: no-cache` for `htdocs/scanner/` files in dev mode, or use a `?v=timestamp` cache buster.

## Component testability matrix

| Component | Without OWRX+? | Without SDR? | Current tests |
|-----------|:-:|:-:|:-:|
| SignalDetector | Yes | Yes | 11 |
| ClassificationPipeline | Yes | Yes | 10 |
| FrequencySweeper | Yes | Yes | 9 |
| ScannerDatabase | Yes | Yes | 8 |
| known_freqs | Yes | Yes | 20 |
| ScannerState | Yes | Yes | 5 |
| ScannerRecorder | Yes | Yes | 0 |
| ScannerService (scan loop) | Yes (mock callbacks) | Yes | 0 |
| SdrBridge | No | No | 0 |
| REST controllers | No | Needs mock | 0 |
| WebSocket integration | No | Needs mock | 0 |
| Mobile UI | Needs server | Needs mock | 0 |
| DSP functions (demod) | Yes | Yes | via e2e only |
