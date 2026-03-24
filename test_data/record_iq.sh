#!/bin/bash
# Record IQ files from SDRplay RSP1a across different bands
# Uses rx_sdr (rx_tools) to capture complex float32 IQ data
set -e

RX_SDR="/tmp/rx_tools/build/rx_sdr"
OUTPUT_DIR="$(dirname "$0")/iq"
mkdir -p "$OUTPUT_DIR"

record() {
    local name="$1" freq="$2" rate="$3" duration="$4" gain="$5"
    local output="$OUTPUT_DIR/${name}.cf32"
    local meta="$OUTPUT_DIR/${name}.json"
    local num_samples=$((rate * duration))

    echo ""
    echo "============================================================"
    echo "Recording: $name"
    echo "  Freq: $(echo "scale=3; $freq/1000000" | bc) MHz, Rate: $(echo "scale=1; $rate/1000000" | bc) MS/s"
    echo "  Duration: ${duration}s, Gain: $gain"

    # rx_sdr records as cu8 by default, use -F CF32 for complex float32
    timeout $((duration + 5)) "$RX_SDR" \
        -d "driver=sdrplay" \
        -f "$freq" \
        -s "$rate" \
        -g "$gain" \
        -F CF32 \
        -n "$num_samples" \
        "$output" 2>&1 || true

    if [ -f "$output" ]; then
        local size=$(stat -c%s "$output")
        local size_mb=$(echo "scale=1; $size/1000000" | bc)
        echo "  Saved: $output ($size_mb MB)"

        # Write JSON metadata
        cat > "$meta" << METAEOF
{
  "name": "$name",
  "center_freq_hz": $freq,
  "sample_rate": $rate,
  "duration_sec": $duration,
  "format": "cf32",
  "device": "SDRplay RSP1a",
  "gain": $gain,
  "recorded_at": "$(date -Iseconds)",
  "file_size_bytes": $size
}
METAEOF
    else
        echo "  FAILED: no output file"
    fi
}

echo "Recording IQ files from SDRplay RSP1a"
echo "Output: $OUTPUT_DIR"

# FM Broadcast — strong signals guaranteed
record "fm_broadcast_97mhz"       97500000  2400000 3 29
record "fm_broadcast_91mhz"       91500000  2400000 3 29

# NOAA Weather Radio — 162.475 MHz Portland primary
record "noaa_weather_162mhz"     162475000  2400000 5 40

# Air Band — 121.5 MHz emergency
record "airband_121mhz"         121500000  2400000 5 40

# Air Band — Portland approach/departure
record "airband_portland_124mhz" 124000000  2400000 5 40

# 2m Ham — 146.520 national simplex
record "ham_2m_146mhz"          146520000  2400000 5 40

# GMRS/FRS — 462 MHz
record "gmrs_462mhz"            462562500  2400000 5 40

# Marine VHF — Ch 16 (156.800 MHz)
record "marine_vhf_ch16"        156800000  2400000 5 40

# Wide FM broadcast — 6 MHz bandwidth for multiple stations
record "fm_broadcast_wide_6mhz"  97500000  6000000 3 29

# Noise floor reference — quiet frequency
record "noise_floor_450mhz"     450000000  2400000 3 40

# HF CB — 27 MHz
record "hf_cb_27mhz"             27000000  2400000 3 40

echo ""
echo "============================================================"
echo "Done! Files:"
ls -lh "$OUTPUT_DIR"/*.cf32 2>/dev/null || echo "No files recorded"
