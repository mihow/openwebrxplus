/**
 * AudioWorklet processor for scanner audio playback.
 * Ring buffer receives Float32 samples via port.postMessage().
 */
class ScannerAudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super(options);
        var maxSize = (options.processorOptions && options.processorOptions.maxBufferSize) || 48000;
        this.bufferSize = Math.round(maxSize / 128) * 128;
        this.audioBuffer = new Float32Array(this.bufferSize);
        this.inPos = 0;
        this.outPos = 0;
        this.port.addEventListener("message", (m) => {
            if (!(m.data instanceof Float32Array)) return;
            var data = m.data;
            if (this.inPos + data.length <= this.bufferSize) {
                this.audioBuffer.set(data, this.inPos);
            } else {
                var remaining = this.bufferSize - this.inPos;
                this.audioBuffer.set(data.subarray(0, remaining), this.inPos);
                this.audioBuffer.set(data.subarray(remaining));
            }
            this.inPos = (this.inPos + data.length) % this.bufferSize;
        });
        this.port.start();
    }

    process(inputs, outputs) {
        var avail = (this.inPos - this.outPos + this.bufferSize) % this.bufferSize;
        if (avail < 128) {
            outputs[0].forEach((ch) => ch.fill(0));
            return true;
        }
        outputs[0].forEach((ch) => {
            ch.set(this.audioBuffer.subarray(this.outPos, this.outPos + 128));
        });
        this.outPos = (this.outPos + 128) % this.bufferSize;
        return true;
    }
}

registerProcessor("scanner-audio-processor", ScannerAudioProcessor);
