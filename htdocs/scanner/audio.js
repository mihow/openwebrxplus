/**
 * Scanner audio engine — handles ADPCM decoding and Web Audio API playback.
 * Adapted from OpenWebRX+'s AudioEngine for standalone scanner use.
 */

var ScannerAudio = (function() {
    var audioContext = null;
    var workletNode = null;
    var gainNode = null;
    var started = false;
    var codec = null;
    var outputRate = 12000;

    // IMA ADPCM codec (matches OpenWebRX+ wire format)
    function ImaAdpcmCodec() {
        this.reset();
    }

    ImaAdpcmCodec.prototype.reset = function() {
        this.predictor = 0;
        this.stepIndex = 0;
    };

    ImaAdpcmCodec.STEP_TABLE = [
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31,
        34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143,
        157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658,
        724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024,
        3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
        15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767
    ];

    ImaAdpcmCodec.INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8];

    ImaAdpcmCodec.prototype.decode = function(data) {
        var output = new Int16Array(data.length * 2);
        var outIdx = 0;

        for (var i = 0; i < data.length; i++) {
            var byte = data[i];
            output[outIdx++] = this._decodeSample(byte & 0x0f);
            output[outIdx++] = this._decodeSample((byte >> 4) & 0x0f);
        }

        return output;
    };

    ImaAdpcmCodec.prototype._decodeSample = function(nibble) {
        var step = ImaAdpcmCodec.STEP_TABLE[this.stepIndex];
        var diff = step >> 3;
        if (nibble & 1) diff += step >> 2;
        if (nibble & 2) diff += step >> 1;
        if (nibble & 4) diff += step;
        if (nibble & 8) diff = -diff;

        this.predictor = Math.max(-32768, Math.min(32767, this.predictor + diff));
        this.stepIndex = Math.max(0, Math.min(88, this.stepIndex + ImaAdpcmCodec.INDEX_TABLE[nibble & 7]));

        return this.predictor;
    };

    function init() {
        if (audioContext) return Promise.resolve();

        var ctxClass = window.AudioContext || window.webkitAudioContext;
        if (!ctxClass) {
            return Promise.reject(new Error("Web Audio API not supported"));
        }

        audioContext = new ctxClass({ latencyHint: "playback" });
        codec = new ImaAdpcmCodec();

        gainNode = audioContext.createGain();
        gainNode.connect(audioContext.destination);

        // Try AudioWorklet, fall back to ScriptProcessor
        if (audioContext.audioWorklet) {
            return audioContext.audioWorklet
                .addModule("static/scanner/scanner-audio-processor.js")
                .then(function() {
                    workletNode = new AudioWorkletNode(audioContext, "scanner-audio-processor", {
                        processorOptions: { maxBufferSize: outputRate * 3 },
                        outputChannelCount: [1],
                    });
                    workletNode.connect(gainNode);
                    started = true;
                })
                .catch(function() {
                    _initScriptProcessor();
                });
        } else {
            _initScriptProcessor();
            return Promise.resolve();
        }
    }

    // Fallback for browsers without AudioWorklet
    var scriptNode = null;
    var fallbackBuffer = new Float32Array(0);
    var fallbackReadPos = 0;

    function _initScriptProcessor() {
        scriptNode = audioContext.createScriptProcessor(1024, 0, 1);
        scriptNode.onaudioprocess = function(e) {
            var output = e.outputBuffer.getChannelData(0);
            var available = fallbackBuffer.length - fallbackReadPos;
            if (available >= output.length) {
                output.set(fallbackBuffer.subarray(fallbackReadPos, fallbackReadPos + output.length));
                fallbackReadPos += output.length;
            } else {
                output.fill(0);
            }
        };
        scriptNode.connect(gainNode);
        started = true;
    }

    function processAudioData(data) {
        if (!started || !audioContext) return;

        // data is a Uint8Array from the WebSocket binary message
        // Skip first byte (message type tag 0x02)
        var audioBytes = data.subarray(1);

        // Check for SYNC word and strip it
        var syncWord = "SYNC";
        var decoded;

        // ADPCM decode
        decoded = codec.decode(audioBytes);

        // Convert Int16 to Float32 for Web Audio
        var floats = new Float32Array(decoded.length);
        for (var i = 0; i < decoded.length; i++) {
            floats[i] = decoded[i] / 32768.0;
        }

        // Resample from outputRate to audioContext.sampleRate
        var resampled = _resample(floats, outputRate, audioContext.sampleRate);

        if (workletNode) {
            workletNode.port.postMessage(resampled);
        } else if (scriptNode) {
            // Append to fallback buffer
            var newBuf = new Float32Array(fallbackBuffer.length - fallbackReadPos + resampled.length);
            newBuf.set(fallbackBuffer.subarray(fallbackReadPos));
            newBuf.set(resampled, fallbackBuffer.length - fallbackReadPos);
            fallbackBuffer = newBuf;
            fallbackReadPos = 0;
        }
    }

    function _resample(input, fromRate, toRate) {
        if (fromRate === toRate) return input;
        var ratio = fromRate / toRate;
        var outLen = Math.floor(input.length / ratio);
        var output = new Float32Array(outLen);
        for (var i = 0; i < outLen; i++) {
            var srcIdx = i * ratio;
            var idx = Math.floor(srcIdx);
            var frac = srcIdx - idx;
            var s0 = input[idx] || 0;
            var s1 = input[idx + 1] || 0;
            output[i] = s0 + frac * (s1 - s0);
        }
        return output;
    }

    function stop() {
        if (codec) codec.reset();
        // Don't close audioContext — just stop feeding data
    }

    function resume() {
        if (audioContext && audioContext.state !== "running") {
            audioContext.resume();
        }
    }

    function setVolume(vol) {
        if (gainNode) gainNode.gain.value = vol;
    }

    function isStarted() {
        return started;
    }

    function playTestTone(durationSec, frequency) {
        durationSec = durationSec || 2;
        frequency = frequency || 440;

        // Ensure audio context is initialized
        if (!audioContext) {
            var ctxClass = window.AudioContext || window.webkitAudioContext;
            audioContext = new ctxClass({ latencyHint: "playback" });
        }
        if (audioContext.state !== "running") {
            audioContext.resume();
        }

        var osc = audioContext.createOscillator();
        var gain = audioContext.createGain();
        osc.type = "sine";
        osc.frequency.value = frequency;
        gain.gain.value = 0.3;
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.start();
        osc.stop(audioContext.currentTime + durationSec);

        return new Promise(function(resolve) {
            setTimeout(resolve, durationSec * 1000);
        });
    }

    function playRecording(detectionId) {
        // Ensure audio context is initialized
        if (!audioContext) {
            var ctxClass = window.AudioContext || window.webkitAudioContext;
            audioContext = new ctxClass({ latencyHint: "playback" });
        }
        if (audioContext.state !== "running") {
            audioContext.resume();
        }

        return fetch("/api/scanner/recordings/" + detectionId)
            .then(function(r) {
                if (!r.ok) throw new Error("Recording not found");
                return r.arrayBuffer();
            })
            .then(function(buf) {
                return audioContext.decodeAudioData(buf);
            })
            .then(function(audioBuffer) {
                var source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                source.start();
            });
    }

    return {
        init: init,
        processAudioData: processAudioData,
        stop: stop,
        resume: resume,
        setVolume: setVolume,
        isStarted: isStarted,
        playTestTone: playTestTone,
        playRecording: playRecording,
    };
})();
