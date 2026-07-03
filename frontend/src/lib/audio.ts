/**
 * Raw PCM16 audio pipeline for Gemini Live:
 * - MicCapture: getUserMedia -> AudioWorklet -> 16 kHz mono PCM16 base64 chunks
 * - PcmPlayer: schedules streamed 24 kHz PCM16 chunks gaplessly via WebAudio
 * - pcm16ToWavBlob: wraps accumulated model audio into a WAV for AudioPlayer replay
 */

const WORKLET_SOURCE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (channel && channel.length > 0) {
      this.port.postMessage(channel.slice(0));
    }
    return true;
  }
}
registerProcessor("pcm-capture", PcmCaptureProcessor);
`;

const floatTo16 = (float32: Float32Array): Int16Array => {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
};

const downsample = (
  input: Float32Array,
  fromRate: number,
  toRate: number
): Float32Array => {
  if (fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const length = Math.floor(input.length / ratio);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    out[i] = input[Math.floor(i * ratio)];
  }
  return out;
};

export const bytesToBase64 = (bytes: Uint8Array): string => {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
};

export const base64ToBytes = (base64: string): Uint8Array => {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
};

export class MicCapture {
  private context: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;

  constructor(
    private readonly targetRate: number,
    private readonly onChunk: (base64Pcm16: string) => void
  ) {}

  get active(): boolean {
    return this.stream !== null;
  }

  async start(deviceId?: string): Promise<void> {
    await this.stop();
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: deviceId ? { deviceId: { exact: deviceId } } : true,
    });
    this.context = new AudioContext();
    const blob = new Blob([WORKLET_SOURCE], { type: "application/javascript" });
    const url = URL.createObjectURL(blob);
    try {
      await this.context.audioWorklet.addModule(url);
    } finally {
      URL.revokeObjectURL(url);
    }
    this.source = this.context.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.context, "pcm-capture");
    this.node.port.onmessage = (event: MessageEvent<Float32Array>) => {
      const rate = this.context?.sampleRate ?? this.targetRate;
      const resampled = downsample(event.data, rate, this.targetRate);
      const pcm = floatTo16(resampled);
      this.onChunk(bytesToBase64(new Uint8Array(pcm.buffer)));
    };
    this.source.connect(this.node);
  }

  async stop(): Promise<void> {
    this.node?.disconnect();
    this.source?.disconnect();
    this.stream?.getTracks().forEach((track) => track.stop());
    if (this.context && this.context.state !== "closed") {
      await this.context.close();
    }
    this.node = null;
    this.source = null;
    this.stream = null;
    this.context = null;
  }
}

export class PcmPlayer {
  private context: AudioContext | null = null;
  private nextTime = 0;
  private scheduled = new Set<AudioBufferSourceNode>();

  constructor(private readonly onPlaybackChange?: (playing: boolean) => void) {}

  play(base64Pcm16: string, sampleRate: number): void {
    if (!this.context || this.context.state === "closed") {
      this.context = new AudioContext();
      this.nextTime = 0;
    }
    const bytes = base64ToBytes(base64Pcm16);
    const pcm = new Int16Array(bytes.buffer, 0, Math.floor(bytes.length / 2));
    const buffer = this.context.createBuffer(1, pcm.length, sampleRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) {
      channel[i] = pcm[i] / 0x8000;
    }
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    const start = Math.max(this.context.currentTime, this.nextTime);
    source.start(start);
    this.nextTime = start + buffer.duration;
    this.scheduled.add(source);
    this.onPlaybackChange?.(true);
    source.onended = () => {
      this.scheduled.delete(source);
      if (this.scheduled.size === 0) {
        this.onPlaybackChange?.(false);
      }
    };
  }

  /** Stop everything immediately (used on bidi_interruption). */
  flush(): void {
    for (const source of this.scheduled) {
      try {
        source.stop();
      } catch {
        // already stopped
      }
    }
    this.scheduled.clear();
    this.nextTime = 0;
    this.onPlaybackChange?.(false);
  }

  async close(): Promise<void> {
    this.flush();
    if (this.context && this.context.state !== "closed") {
      await this.context.close();
    }
    this.context = null;
  }
}

export const pcm16ToWavBlob = (
  chunks: Uint8Array[],
  sampleRate: number
): Blob => {
  const dataLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataLength, true);
  return new Blob([header, ...(chunks as unknown as BlobPart[])], {
    type: "audio/wav",
  });
};
