"""Bridge between ScannerService and OpenWebRX+'s SdrSource/FftChain.

Creates an FftChain to read raw power spectrum data from the SDR,
and provides retune/fft callbacks for ScannerService.
"""

import logging
import threading

import numpy as np
from csdr.chain.fft import FftChain
from pycsdr.modules import Buffer
from owrx.source import SdrSourceEventClient, SdrSourceState, SdrClientClass

logger = logging.getLogger(__name__)


class SdrBridge(SdrSourceEventClient):
    """Connects ScannerService to an OpenWebRX+ SdrSource.

    Usage:
        bridge = SdrBridge(sdr_source, fft_size=1024)
        bridge.start()
        # bridge.retune(freq_hz) to change center frequency
        # bridge.get_fft() to read current FFT power spectrum
        bridge.stop()
    """

    def __init__(self, sdr_source, fft_size: int = 1024, fft_fps: int = 10):
        self._sdr_source = sdr_source
        self._fft_size = fft_size
        self._fft_fps = fft_fps
        self._fft_chain: FftChain | None = None
        self._output_reader = None
        self._pump_thread: threading.Thread | None = None
        self._latest_fft: np.ndarray | None = None
        self._fft_lock = threading.Lock()
        self._fft_event = threading.Event()
        self._running = False

    def start(self):
        """Register with SdrSource and create FFT chain."""
        if self._running:
            return
        self._running = True
        self._sdr_source.addClient(self)
        logger.info("SdrBridge registered with SDR source")

    def stop(self):
        """Stop FFT chain and unregister from SdrSource."""
        self._running = False
        self._stop_fft()
        self._sdr_source.removeClient(self)
        logger.info("SdrBridge stopped")

    def retune(self, freq_hz: int):
        """Retune the SDR center frequency."""
        self._fft_event.clear()
        self._sdr_source.setCenterFreq(freq_hz)

    def get_fft(self) -> np.ndarray | None:
        """Get the latest FFT power spectrum (blocking until available).

        Returns array of fft_size float32 values in dB, or None on timeout.
        """
        # Wait for at least one FFT frame after last retune
        if not self._fft_event.wait(timeout=2.0):
            return None
        with self._fft_lock:
            return self._latest_fft

    def get_sample_rate(self) -> int:
        """Get the current sample rate from the SDR source."""
        return self._sdr_source.getProps()["samp_rate"]

    # --- SdrSourceEventClient interface ---

    def getClientClass(self) -> SdrClientClass:
        return SdrClientClass.USER

    def onStateChange(self, state: SdrSourceState):
        if state == SdrSourceState.RUNNING:
            self._start_fft()
        elif state == SdrSourceState.STOPPING:
            self._stop_fft()
        elif state == SdrSourceState.STOPPED:
            self._stop_fft()

    def onFail(self):
        self._stop_fft()

    def onShutdown(self):
        self._stop_fft()

    # --- Internal ---

    def _start_fft(self):
        """Create FftChain and start pump thread."""
        if self._fft_chain is not None:
            return

        samp_rate = self.get_sample_rate()
        logger.info(
            "Starting FFT chain: samp_rate=%d, fft_size=%d, fps=%d",
            samp_rate, self._fft_size, self._fft_fps,
        )

        self._fft_chain = FftChain(
            samp_rate=samp_rate,
            fft_size=self._fft_size,
            fft_v_overlap_factor=0.0,
            fft_fps=self._fft_fps,
            fft_compression="none",
        )

        # Connect input from SDR buffer
        self._fft_chain.setReader(self._sdr_source.getBuffer().getReader())

        # Create output buffer and reader
        output_buffer = Buffer(self._fft_chain.getOutputFormat())
        self._fft_chain.setWriter(output_buffer)
        self._output_reader = output_buffer.getReader()

        # Start pump thread
        self._pump_thread = threading.Thread(
            target=self._pump_loop,
            daemon=True,
            name="scanner-fft-pump",
        )
        self._pump_thread.start()

    def _pump_loop(self):
        """Read FFT output and store latest frame."""
        reader = self._output_reader
        while self._running and reader is not None:
            try:
                data = reader.read()
            except ValueError:
                continue
            except BrokenPipeError:
                break
            if data is None or (isinstance(data, bytes) and len(data) == 0):
                break

            # Convert raw bytes to float32 numpy array
            power_db = np.frombuffer(data, dtype=np.float32).copy()
            if len(power_db) == self._fft_size:
                with self._fft_lock:
                    self._latest_fft = power_db
                self._fft_event.set()

    def _stop_fft(self):
        """Stop FFT chain and pump thread."""
        if self._output_reader is not None:
            self._output_reader.stop()
            self._output_reader = None
        if self._fft_chain is not None:
            self._fft_chain.stop()
            self._fft_chain = None
        if self._pump_thread is not None:
            self._pump_thread.join(timeout=3.0)
            self._pump_thread = None
        self._latest_fft = None
        self._fft_event.clear()
