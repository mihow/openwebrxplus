#!/bin/bash
# Record IQ files across all bands likely to have voice activity.
# Uses SDRplay RSP1a via rx_sdr (rx_tools).
#
# Usage:
#   ./scripts/record_bands.sh                    # Record all bands
#   ./scripts/record_bands.sh --band fm          # Record one band
#   ./scripts/record_bands.sh --duration 30      # Custom duration (seconds)
#   ./scripts/record_bands.sh --output-dir /tmp  # Custom output directory
#
# Requires: rx_sdr (build from https://github.com/rxseger/rx_tools)
#   cd /tmp && git clone https://github.com/rxseger/rx_tools.git
#   cd rx_tools && mkdir build && cd build && cmake .. && make
#
# After recording, scan with:
#   python3 scripts/scan_iq.py test_data/iq/*.cf32
#   python3 scripts/analyze_scan.py

set -euo pipefail

RX_SDR="${RX_SDR:-/tmp/rx_tools/build/rx_sdr}"
OUTPUT_DIR="${OUTPUT_DIR:-$(dirname "$0")/../test_data/iq}"
DURATION=10
BAND=""
GAIN_VHF=40
GAIN_UHF=40
GAIN_FM=29
GAIN_HF=29
DEVICE="driver=sdrplay"

usage() {
    echo "Usage: $0 [--band BAND] [--duration SEC] [--output-dir DIR]"
    echo ""
    echo "Bands: fm, noaa, airband, 2m, 70cm, gmrs, marine, hf, all (default)"
    echo ""
    echo "Examples:"
    echo "  $0                          # All bands, 10 sec each"
    echo "  $0 --band noaa --duration 30"
    echo "  $0 --band fm --duration 15"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --band) BAND="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) echo "Unknown arg: $1"; usage ;;
    esac
done

if ! command -v "$RX_SDR" &>/dev/null; then
    echo "ERROR: rx_sdr not found at $RX_SDR"
    echo "Build it: cd /tmp && git clone https://github.com/rxseger/rx_tools.git && cd rx_tools && mkdir build && cd build && cmake .. && make"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

record() {
    local name="$1" freq="$2" rate="$3" gain="$4" dur="${5:-$DURATION}"
    local num_samples=$((rate * dur))
    local output="$OUTPUT_DIR/${name}_${TIMESTAMP}.cf32"
    local meta="$OUTPUT_DIR/${name}_${TIMESTAMP}.json"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $name"
    echo "  $(echo "scale=3; $freq/1000000" | bc) MHz  |  $(echo "scale=1; $rate/1000000" | bc) MS/s  |  ${dur}s  |  gain=$gain"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    timeout $((dur + 10)) "$RX_SDR" \
        -d "$DEVICE" \
        -f "$freq" \
        -s "$rate" \
        -g "$gain" \
        -F CF32 \
        -n "$num_samples" \
        "$output" 2>&1 | grep -v "^\[" | grep -v "^$" || true

    if [ -f "$output" ]; then
        local size=$(stat -c%s "$output")
        local size_mb=$(echo "scale=1; $size/1000000" | bc)
        echo "  Saved: $(basename "$output") ($size_mb MB)"

        cat > "$meta" << METAEOF
{
  "name": "$name",
  "center_freq_hz": $freq,
  "sample_rate": $rate,
  "duration_sec": $dur,
  "format": "cf32",
  "device": "SDRplay RSP1a",
  "gain": $gain,
  "recorded_at": "$(date -Iseconds)"
}
METAEOF
    else
        echo "  FAILED"
    fi
}

record_fm() {
    # FM broadcast — 6 MHz captures ~6 stations
    # Portland: KOPB 91.5, KGON 92.3, KNRK 94.7, KBFF 95.5, KYCH 97.1, KUPL 98.7
    record "fm_low_91mhz"   91500000  6000000 $GAIN_FM
    record "fm_high_101mhz" 101000000 6000000 $GAIN_FM
}

record_noaa() {
    # NOAA Weather — all 7 channels fit in 1 MHz
    record "noaa_weather"  162475000 1000000 $GAIN_VHF 15
}

record_airband() {
    # Air band — PDX tower, approach, emergency
    record "airband_pdx"   125000000 6000000 $GAIN_VHF 15
}

record_2m() {
    # 2m ham — simplex + repeater outputs
    record "ham_2m_simplex" 146500000 2400000 $GAIN_VHF 15
    record "ham_2m_repeaters" 147000000 2400000 $GAIN_VHF 15
}

record_70cm() {
    # 70cm ham — repeaters, Mount Scott, KOIN tower
    record "ham_70cm_440mhz" 441000000 6000000 $GAIN_UHF 15
    record "ham_70cm_443mhz" 443500000 6000000 $GAIN_UHF 15
}

record_gmrs() {
    # GMRS/FRS — all channels in 6 MHz
    record "gmrs_frs"      465000000 6000000 $GAIN_UHF 15
}

record_marine() {
    # Marine VHF — Ch16 and surrounding
    record "marine_vhf"    157000000 2400000 $GAIN_VHF 15
}

record_hf() {
    # HF — CB and 10m/20m ham
    record "hf_cb_27mhz"    27000000 2400000 $GAIN_HF
    record "hf_10m"          28500000 2400000 $GAIN_HF
}

# Run requested bands
case "${BAND:-all}" in
    fm)      record_fm ;;
    noaa)    record_noaa ;;
    airband) record_airband ;;
    2m)      record_2m ;;
    70cm)    record_70cm ;;
    gmrs)    record_gmrs ;;
    marine)  record_marine ;;
    hf)      record_hf ;;
    all)
        record_fm
        record_noaa
        record_airband
        record_2m
        record_70cm
        record_gmrs
        record_marine
        record_hf
        ;;
    *) echo "Unknown band: $BAND"; usage ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done! Files in: $OUTPUT_DIR"
echo ""
echo "  Scan:    python3 scripts/scan_iq.py $OUTPUT_DIR/*_${TIMESTAMP}.cf32"
echo "  Analyze: python3 scripts/analyze_scan.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
