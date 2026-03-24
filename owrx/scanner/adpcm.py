"""IMA ADPCM decoder for tapping the DSP chain's audio output.

Decodes the ADPCM+SYNC wire format that OpenWebRX+ sends to clients,
producing Float32 PCM samples suitable for the ScannerRecorder.
"""

import numpy as np

STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31,
    34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143,
    157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658,
    724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024,
    3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
]

INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8]

SYNC_WORD = b"SYNC"


class AdpcmDecoder:
    """Stateful IMA ADPCM decoder matching OpenWebRX+ SYNC wire format."""

    def __init__(self):
        self.predictor = 0
        self.step_index = 0
        self.phase = 0  # 0=searching SYNC, 1=reading state, 2=decoding
        self.sync_pos = 0
        self.sync_buf = bytearray(4)
        self.sync_buf_idx = 0
        self.sync_counter = 0

    def decode(self, data: bytes) -> np.ndarray:
        """Decode ADPCM+SYNC data, return Float32 PCM samples in [-1, 1]."""
        out = np.empty(len(data) * 2, dtype=np.int16)
        oi = 0

        for byte in data:
            if self.phase == 0:
                # Search for SYNC word
                if byte == SYNC_WORD[self.sync_pos]:
                    self.sync_pos += 1
                else:
                    self.sync_pos = 0
                if self.sync_pos == 4:
                    self.sync_buf_idx = 0
                    self.phase = 1
            elif self.phase == 1:
                # Read 4 bytes of codec state
                self.sync_buf[self.sync_buf_idx] = byte
                self.sync_buf_idx += 1
                if self.sync_buf_idx == 4:
                    self.step_index = int.from_bytes(self.sync_buf[0:2], "little", signed=True)
                    self.predictor = int.from_bytes(self.sync_buf[2:4], "little", signed=True)
                    self.sync_counter = 1000
                    self.phase = 2
            elif self.phase == 2:
                # Decode two samples per byte
                out[oi] = self._decode_nibble(byte & 0x0F)
                oi += 1
                out[oi] = self._decode_nibble((byte >> 4) & 0x0F)
                oi += 1
                self.sync_counter -= 1
                if self.sync_counter == 0:
                    self.sync_pos = 0
                    self.phase = 0

        # Convert Int16 to Float32
        return out[:oi].astype(np.float32) / 32768.0

    def _decode_nibble(self, nibble: int) -> int:
        step = STEP_TABLE[self.step_index]
        diff = step >> 3
        if nibble & 1:
            diff += step >> 2
        if nibble & 2:
            diff += step >> 1
        if nibble & 4:
            diff += step
        if nibble & 8:
            diff = -diff
        self.predictor = max(-32768, min(32767, self.predictor + diff))
        self.step_index = max(0, min(88, self.step_index + INDEX_TABLE[nibble & 7]))
        return self.predictor
