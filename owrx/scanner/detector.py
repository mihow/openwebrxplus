import numpy as np


class SignalDetector:
    def __init__(
        self,
        fft_size: int,
        sample_rate: float,
        snr_threshold_db: float = 10.0,
        noise_alpha: float = 0.1,
        min_signal_bins: int = 3,
        merge_gap_bins: int = 10,
    ):
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.snr_threshold_db = snr_threshold_db
        self.noise_alpha = noise_alpha
        self.min_signal_bins = min_signal_bins
        self.merge_gap_bins = merge_gap_bins
        self.noise_floor_db: float | None = None
        self._bin_width = sample_rate / fft_size

    def _bin_to_freq(self, bin_idx: int, center_freq: float) -> float:
        """Convert FFT bin index to frequency in Hz.

        Bin 0 = center_freq - sample_rate/2
        Bin N/2 = center_freq
        Bin N-1 = center_freq + sample_rate/2 - bin_width
        """
        return center_freq - self.sample_rate / 2 + bin_idx * self._bin_width

    def detect(self, fft_power_db: np.ndarray, center_freq: float) -> list[dict]:
        """Detect signals in an FFT power spectrum.

        Args:
            fft_power_db: Array of FFT bin power levels in dB.
            center_freq: Center frequency of the FFT in Hz.

        Returns:
            List of signal dicts sorted by peak_power_db descending.
            Each dict has: frequency_hz, bandwidth_hz, peak_power_db, snr_db.
        """
        # 1. Estimate noise floor as median of all bins
        current_noise = float(np.median(fft_power_db))

        # 2. Update running noise floor with IIR filter
        if self.noise_floor_db is None:
            self.noise_floor_db = current_noise
        else:
            self.noise_floor_db += self.noise_alpha * (current_noise - self.noise_floor_db)

        # 3. Threshold
        threshold = self.noise_floor_db + self.snr_threshold_db

        # 4. Find contiguous runs of bins above threshold
        above = fft_power_db > threshold
        raw_runs = []
        run_start = None

        for i in range(len(above)):
            if above[i] and run_start is None:
                run_start = i
            elif not above[i] and run_start is not None:
                raw_runs.append((run_start, i))
                run_start = None

        # Handle run that extends to end
        if run_start is not None:
            raw_runs.append((run_start, len(above)))

        # 5. Merge runs that are separated by fewer than merge_gap_bins
        merged = []
        for start, end in raw_runs:
            if merged and start - merged[-1][1] < self.merge_gap_bins:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))

        # 6. Filter by minimum width
        signals = [(s, e) for s, e in merged if e - s >= self.min_signal_bins]

        # 7. Extract signal parameters
        results = []
        for start, end in signals:
            segment = fft_power_db[start:end]
            peak_idx = start + int(np.argmax(segment))
            peak_power = float(segment.max())
            snr = peak_power - self.noise_floor_db

            # Center frequency: weighted mean of bin indices by power (linear)
            bin_indices = np.arange(start, end)
            linear_power = 10 ** (segment / 10)
            weighted_center = float(np.average(bin_indices, weights=linear_power))

            freq = self._bin_to_freq(weighted_center, center_freq)
            bandwidth = (end - start) * self._bin_width

            results.append({
                "frequency_hz": freq,
                "bandwidth_hz": bandwidth,
                "peak_power_db": peak_power,
                "snr_db": snr,
            })

        # 8. Sort by peak power descending
        results.sort(key=lambda s: s["peak_power_db"], reverse=True)
        return results

    def detect_from_iq(
        self,
        iq_samples: np.ndarray,
        center_freq: float,
        num_averages: int = 8,
    ) -> list[dict]:
        """Compute averaged FFT power from raw IQ samples and detect signals.

        Args:
            iq_samples: Complex64 (cf32) IQ samples.
            center_freq: Center frequency in Hz.
            num_averages: Number of FFT frames to average for smoothing.

        Returns:
            List of detected signal dicts (same format as detect()).
        """
        n = self.fft_size
        num_frames = min(num_averages, len(iq_samples) // n)
        if num_frames < 1:
            return []

        # Accumulate power across frames
        power_accum = np.zeros(n, dtype=np.float64)
        window = np.hanning(n)

        for i in range(num_frames):
            frame = iq_samples[i * n : (i + 1) * n]
            spectrum = np.fft.fftshift(np.fft.fft(frame * window))
            power_accum += np.abs(spectrum) ** 2

        power_accum /= num_frames

        # Convert to dB
        fft_power_db = 10.0 * np.log10(power_accum + 1e-20)

        return self.detect(fft_power_db, center_freq)
