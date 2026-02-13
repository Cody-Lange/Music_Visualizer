import { useRef, useCallback, useEffect, useState } from "react";
import { getFrequencyData, getEnergyBands, getTimeDomainData } from "@/lib/audio-context";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";

/**
 * Real-time audio feature extraction hook.
 * Provides per-frame audio features for driving visualizations.
 */
export function useAudioFeatures() {
  const [features, setFeatures] = useState<AudioFeaturesAtTime | null>(null);
  const [beatState, setBeatState] = useState<BeatState>({
    isOnBeat: false,
    beatIndex: -1,
    timeSinceLastBeat: 0,
    timeToNextBeat: 0,
    beatIntensity: 0,
  });

  const animFrameRef = useRef<number>(0);
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const currentTime = useAudioStore((s) => s.currentTime);
  const analysis = useAnalysisStore((s) => s.analysis);

  const beats = analysis?.rhythm.beats ?? [];

  const updateFeatures = useCallback(() => {
    const freqData = getFrequencyData();
    const timeData = getTimeDomainData();

    // Compute RMS from time domain
    let rmsSum = 0;
    for (let i = 0; i < timeData.length; i++) {
      const val = ((timeData[i] ?? 128) - 128) / 128;
      rmsSum += val * val;
    }
    const rms = Math.sqrt(rmsSum / timeData.length);

    // Energy bands
    const bands = getEnergyBands(freqData);

    // Spectral centroid (weighted average of frequencies)
    let weightedSum = 0;
    let totalMagnitude = 0;
    for (let i = 0; i < freqData.length; i++) {
      const mag = freqData[i] ?? 0;
      weightedSum += i * mag;
      totalMagnitude += mag;
    }
    const spectralCentroid = totalMagnitude > 0 ? weightedSum / totalMagnitude / freqData.length : 0.5;

    setFeatures({
      rms,
      spectralCentroid,
      spectralFlux: 0, // Would need previous frame comparison
      spectralRolloff: 0,
      spectralFlatness: 0,
      energyBands: bands,
      harmonicEnergy: bands.mid + bands.lowMid,
      percussiveEnergy: bands.bass + bands.treble,
      onsetStrength: bands.bass * 2,
    });

    // Beat state
    const time = currentTime;
    let lastBeatIdx = -1;
    let nextBeatIdx = -1;

    for (let i = 0; i < beats.length; i++) {
      if ((beats[i] ?? 0) <= time) {
        lastBeatIdx = i;
      } else {
        nextBeatIdx = i;
        break;
      }
    }

    const lastBeatTime = lastBeatIdx >= 0 ? (beats[lastBeatIdx] ?? 0) : 0;
    const nextBeatTime = nextBeatIdx >= 0 ? (beats[nextBeatIdx] ?? 0) : (analysis?.metadata.duration ?? 0);
    const timeSinceLastBeat = time - lastBeatTime;
    const timeToNextBeat = nextBeatTime - time;
    const isOnBeat = timeSinceLastBeat < 0.08; // Within 80ms of beat
    const beatIntensity = isOnBeat ? Math.max(0, 1 - timeSinceLastBeat / 0.08) : 0;

    setBeatState({
      isOnBeat,
      beatIndex: lastBeatIdx,
      timeSinceLastBeat,
      timeToNextBeat,
      beatIntensity,
    });

    if (isPlaying) {
      animFrameRef.current = requestAnimationFrame(updateFeatures);
    }
  }, [isPlaying, currentTime, beats, analysis]);

  useEffect(() => {
    if (isPlaying) {
      animFrameRef.current = requestAnimationFrame(updateFeatures);
    }
    return () => {
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [isPlaying, updateFeatures]);

  return { features, beatState };
}
