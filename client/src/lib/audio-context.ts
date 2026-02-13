/**
 * Singleton AudioContext manager.
 * Ensures a single AudioContext instance shared across the application.
 */

let audioContext: AudioContext | null = null;
let analyserNode: AnalyserNode | null = null;
let sourceNode: MediaElementAudioSourceNode | null = null;
let connectedElement: HTMLMediaElement | null = null;

export function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  return audioContext;
}

export function getAnalyserNode(): AnalyserNode {
  if (!analyserNode) {
    const ctx = getAudioContext();
    analyserNode = ctx.createAnalyser();
    analyserNode.fftSize = 2048;
    analyserNode.smoothingTimeConstant = 0.8;
    analyserNode.connect(ctx.destination);
  }
  return analyserNode;
}

export function connectAudioElement(element: HTMLMediaElement): void {
  // Avoid reconnecting the same element
  if (connectedElement === element) return;

  const ctx = getAudioContext();
  const analyser = getAnalyserNode();

  // Disconnect previous source
  if (sourceNode) {
    try {
      sourceNode.disconnect();
    } catch {
      // Already disconnected
    }
  }

  sourceNode = ctx.createMediaElementSource(element);
  sourceNode.connect(analyser);
  connectedElement = element;
}

export function getFrequencyData(): Uint8Array {
  const analyser = getAnalyserNode();
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(data);
  return data;
}

export function getTimeDomainData(): Uint8Array {
  const analyser = getAnalyserNode();
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(data);
  return data;
}

/**
 * Extract energy in specific frequency bands from FFT data.
 */
export function getEnergyBands(frequencyData: Uint8Array): {
  bass: number;
  lowMid: number;
  mid: number;
  highMid: number;
  treble: number;
} {
  const bins = frequencyData.length;
  // Approximate frequency band splits for 1024 bins at 44100 Hz
  const bassEnd = Math.floor(bins * 0.04);      // ~860 Hz
  const lowMidEnd = Math.floor(bins * 0.08);     // ~1720 Hz
  const midEnd = Math.floor(bins * 0.25);        // ~5380 Hz
  const highMidEnd = Math.floor(bins * 0.5);     // ~10760 Hz

  const avg = (start: number, end: number) => {
    let sum = 0;
    const count = end - start;
    if (count <= 0) return 0;
    for (let i = start; i < end; i++) {
      sum += frequencyData[i] ?? 0;
    }
    return sum / count / 255; // Normalize to 0-1
  };

  return {
    bass: avg(0, bassEnd),
    lowMid: avg(bassEnd, lowMidEnd),
    mid: avg(lowMidEnd, midEnd),
    highMid: avg(midEnd, highMidEnd),
    treble: avg(highMidEnd, bins),
  };
}
