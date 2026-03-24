"""Scanner configuration keys.

These are registered in owrx/config/defaults.py and accessible via Config.get().
Keys are prefixed with 'scanner_' to avoid collisions.
"""

SCANNER_CONFIG_KEYS = [
    "scanner_enabled",
    "scanner_freq_start",
    "scanner_freq_stop",
    "scanner_dwell_time_ms",
    "scanner_squelch_threshold",
    "scanner_hang_time_ms",
    "scanner_demod_mode",
    "scanner_content_filter",
    "scanner_record_mode",
    "scanner_storage_path",
    "scanner_max_storage_mb",
    "scanner_max_clip_sec",
    "scanner_retention_days",
    "scanner_recording_kbps",
]
