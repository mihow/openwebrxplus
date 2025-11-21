#!/usr/bin/env python3
"""
Generate synthetic IQ test files for OpenWebRX+ testing.

Creates complex float32 (.cf32) files with simple test signals.
These can be used to test the FileSource and DSP chain.
"""

import struct
import math
import argparse
import json
from pathlib import Path


def generate_tone(frequency: float, sample_rate: int, duration: float, amplitude: float = 0.5):
    """
    Generate a single tone (carrier) as IQ samples.

    Args:
        frequency: Tone frequency offset from center (Hz)
        sample_rate: Sample rate (Hz)
        duration: Duration in seconds
        amplitude: Signal amplitude (0-1)

    Yields:
        Tuples of (I, Q) float samples
    """
    num_samples = int(sample_rate * duration)
    for i in range(num_samples):
        t = i / sample_rate
        phase = 2 * math.pi * frequency * t
        # Complex exponential: e^(j*phase) = cos(phase) + j*sin(phase)
        i_sample = amplitude * math.cos(phase)
        q_sample = amplitude * math.sin(phase)
        yield (i_sample, q_sample)


def generate_noise(sample_rate: int, duration: float, amplitude: float = 0.1):
    """
    Generate white noise as IQ samples using simple LCG PRNG.

    Args:
        sample_rate: Sample rate (Hz)
        duration: Duration in seconds
        amplitude: Noise amplitude (0-1)

    Yields:
        Tuples of (I, Q) float samples
    """
    import random
    num_samples = int(sample_rate * duration)
    for _ in range(num_samples):
        i_sample = amplitude * (random.random() * 2 - 1)
        q_sample = amplitude * (random.random() * 2 - 1)
        yield (i_sample, q_sample)


def generate_am_signal(
    carrier_freq: float,
    mod_freq: float,
    sample_rate: int,
    duration: float,
    carrier_amplitude: float = 0.5,
    mod_depth: float = 0.5
):
    """
    Generate AM modulated signal.

    Args:
        carrier_freq: Carrier frequency offset from center (Hz)
        mod_freq: Modulation frequency (Hz)
        sample_rate: Sample rate (Hz)
        duration: Duration in seconds
        carrier_amplitude: Carrier amplitude (0-1)
        mod_depth: Modulation depth (0-1)

    Yields:
        Tuples of (I, Q) float samples
    """
    num_samples = int(sample_rate * duration)
    for i in range(num_samples):
        t = i / sample_rate
        # AM: A(t) = Ac * (1 + m * sin(2*pi*fm*t)) * cos(2*pi*fc*t)
        modulation = 1 + mod_depth * math.sin(2 * math.pi * mod_freq * t)
        carrier_phase = 2 * math.pi * carrier_freq * t
        amplitude = carrier_amplitude * modulation
        i_sample = amplitude * math.cos(carrier_phase)
        q_sample = amplitude * math.sin(carrier_phase)
        yield (i_sample, q_sample)


def write_cf32(filename: str, samples):
    """
    Write IQ samples to a complex float32 file.

    Args:
        filename: Output filename
        samples: Iterator of (I, Q) tuples
    """
    with open(filename, 'wb') as f:
        for i_sample, q_sample in samples:
            # Write as interleaved float32 (little-endian)
            f.write(struct.pack('<ff', i_sample, q_sample))


def write_metadata(filename: str, metadata: dict):
    """Write JSON metadata file."""
    json_file = Path(filename).with_suffix('.json')
    with open(json_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic IQ test files')
    parser.add_argument('--output', '-o', default='test_data/iq/test_tone.cf32',
                        help='Output filename')
    parser.add_argument('--sample-rate', '-s', type=int, default=48000,
                        help='Sample rate in Hz')
    parser.add_argument('--duration', '-d', type=float, default=5.0,
                        help='Duration in seconds')
    parser.add_argument('--signal', choices=['tone', 'noise', 'am', 'tone_noise'],
                        default='tone', help='Signal type')
    parser.add_argument('--frequency', '-f', type=float, default=1000,
                        help='Tone frequency offset from center (Hz)')
    parser.add_argument('--center-freq', type=int, default=14074000,
                        help='Center frequency for metadata (Hz)')

    args = parser.parse_args()

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.signal} signal...")
    print(f"  Sample rate: {args.sample_rate} Hz")
    print(f"  Duration: {args.duration} s")
    print(f"  Output: {args.output}")

    if args.signal == 'tone':
        samples = generate_tone(args.frequency, args.sample_rate, args.duration)
        description = f"{args.frequency}Hz tone"
    elif args.signal == 'noise':
        samples = generate_noise(args.sample_rate, args.duration)
        description = "White noise"
    elif args.signal == 'am':
        samples = generate_am_signal(args.frequency, 400, args.sample_rate, args.duration)
        description = f"AM signal at {args.frequency}Hz with 400Hz modulation"
    elif args.signal == 'tone_noise':
        # Combine tone and noise
        def combined():
            tone_gen = generate_tone(args.frequency, args.sample_rate, args.duration, 0.4)
            noise_gen = generate_noise(args.sample_rate, args.duration, 0.1)
            for (ti, tq), (ni, nq) in zip(tone_gen, noise_gen):
                yield (ti + ni, tq + nq)
        samples = combined()
        description = f"{args.frequency}Hz tone with noise"

    write_cf32(args.output, samples)

    # Calculate file size
    file_size = Path(args.output).stat().st_size
    expected_samples = int(args.sample_rate * args.duration)

    # Write metadata
    metadata = {
        "sample_rate": args.sample_rate,
        "center_frequency": args.center_freq,
        "duration_seconds": args.duration,
        "description": description,
        "signal_type": args.signal,
        "file_size_bytes": file_size,
        "num_samples": expected_samples
    }
    write_metadata(args.output, metadata)

    print(f"  File size: {file_size} bytes ({expected_samples} samples)")
    print(f"  Metadata written to: {Path(args.output).with_suffix('.json')}")
    print("Done!")


if __name__ == '__main__':
    main()
