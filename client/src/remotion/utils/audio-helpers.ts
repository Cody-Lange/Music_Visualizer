import type { AudioAnalysis } from "@/types/audio";
import type { SectionSpec } from "@/types/render";

/**
 * Get the current section for a given time.
 */
export function getCurrentSection(
  sections: SectionSpec[],
  currentTime: number,
): SectionSpec | null {
  for (let i = sections.length - 1; i >= 0; i--) {
    if (currentTime >= (sections[i]?.startTime ?? 0)) {
      return sections[i] ?? null;
    }
  }
  return sections[0] ?? null;
}

/**
 * Get beat state at a given time.
 */
export function getBeatStateAtTime(
  beats: number[],
  currentTime: number,
): { isOnBeat: boolean; intensity: number; index: number } {
  let lastBeatIdx = -1;
  for (let i = 0; i < beats.length; i++) {
    if ((beats[i] ?? 0) <= currentTime) {
      lastBeatIdx = i;
    } else {
      break;
    }
  }

  const lastBeatTime = lastBeatIdx >= 0 ? (beats[lastBeatIdx] ?? 0) : 0;
  const timeSince = currentTime - lastBeatTime;
  const isOnBeat = timeSince < 0.08;
  const intensity = isOnBeat ? Math.max(0, 1 - timeSince / 0.08) : 0;

  return { isOnBeat, intensity, index: lastBeatIdx };
}

/**
 * Interpolate an audio feature value at a specific time
 * from the analysis time series.
 */
export function interpolateFeature(
  times: number[],
  values: number[],
  targetTime: number,
): number {
  if (times.length === 0 || values.length === 0) return 0;

  // Binary search for the nearest time index
  let lo = 0;
  let hi = times.length - 1;

  if (targetTime <= (times[0] ?? 0)) return values[0] ?? 0;
  if (targetTime >= (times[hi] ?? 0)) return values[hi] ?? 0;

  while (lo < hi - 1) {
    const mid = Math.floor((lo + hi) / 2);
    if ((times[mid] ?? 0) <= targetTime) {
      lo = mid;
    } else {
      hi = mid;
    }
  }

  // Linear interpolation
  const t0 = times[lo] ?? 0;
  const t1 = times[hi] ?? 0;
  const v0 = values[lo] ?? 0;
  const v1 = values[hi] ?? 0;

  if (t1 === t0) return v0;
  const ratio = (targetTime - t0) / (t1 - t0);
  return v0 + (v1 - v0) * ratio;
}

/**
 * Get a complete set of audio features interpolated at a specific time.
 */
export function getAudioFeaturesAtTime(
  analysis: AudioAnalysis,
  currentTime: number,
) {
  const { spectral } = analysis;
  return {
    rms: interpolateFeature(spectral.times, spectral.rms, currentTime),
    spectralCentroid: interpolateFeature(spectral.times, spectral.spectralCentroid, currentTime),
    bass: interpolateFeature(spectral.times, spectral.energyBands.bass, currentTime),
    mid: interpolateFeature(spectral.times, spectral.energyBands.mid, currentTime),
    treble: interpolateFeature(spectral.times, spectral.energyBands.treble, currentTime),
    harmonicEnergy: interpolateFeature(spectral.times, analysis.harmonicPercussive.harmonicEnergy, currentTime),
    percussiveEnergy: interpolateFeature(spectral.times, analysis.harmonicPercussive.percussiveEnergy, currentTime),
  };
}
