import { describe, it, expect } from "vitest";
import {
  getCurrentSection,
  getBeatStateAtTime,
  interpolateFeature,
  getAudioFeaturesAtTime,
} from "@/remotion/utils/audio-helpers";
import type { SectionSpec } from "@/types/render";
import type { AudioAnalysis } from "@/types/audio";

// --- getCurrentSection ---

describe("getCurrentSection", () => {
  const sections: SectionSpec[] = [
    { label: "intro", startTime: 0, endTime: 30 } as SectionSpec,
    { label: "verse", startTime: 30, endTime: 90 } as SectionSpec,
    { label: "chorus", startTime: 90, endTime: 150 } as SectionSpec,
  ];

  it("returns first section for time 0", () => {
    const result = getCurrentSection(sections, 0);
    expect(result?.label).toBe("intro");
  });

  it("returns correct section for mid-section time", () => {
    const result = getCurrentSection(sections, 60);
    expect(result?.label).toBe("verse");
  });

  it("returns last section for time at boundary", () => {
    const result = getCurrentSection(sections, 90);
    expect(result?.label).toBe("chorus");
  });

  it("returns last section for time past all sections", () => {
    const result = getCurrentSection(sections, 200);
    expect(result?.label).toBe("chorus");
  });

  it("returns first section for negative time", () => {
    const result = getCurrentSection(sections, -5);
    expect(result?.label).toBe("intro");
  });

  it("returns null for empty sections array", () => {
    const result = getCurrentSection([], 10);
    expect(result).toBeNull();
  });
});

// --- getBeatStateAtTime ---

describe("getBeatStateAtTime", () => {
  const beats = [0.0, 0.5, 1.0, 1.5, 2.0];

  it("is on beat when exactly at beat time", () => {
    const result = getBeatStateAtTime(beats, 0.5);
    expect(result.isOnBeat).toBe(true);
    expect(result.intensity).toBeCloseTo(1.0);
    expect(result.index).toBe(1);
  });

  it("is on beat within 80ms threshold", () => {
    const result = getBeatStateAtTime(beats, 0.54); // 40ms after beat at 0.5
    expect(result.isOnBeat).toBe(true);
    expect(result.intensity).toBeGreaterThan(0);
    expect(result.intensity).toBeLessThan(1);
  });

  it("is not on beat after threshold", () => {
    const result = getBeatStateAtTime(beats, 0.6); // 100ms after beat
    expect(result.isOnBeat).toBe(false);
    expect(result.intensity).toBe(0);
  });

  it("returns correct index for last beat", () => {
    const result = getBeatStateAtTime(beats, 2.0);
    expect(result.index).toBe(4);
  });

  it("returns -1 index before first beat", () => {
    const result = getBeatStateAtTime(beats, -1);
    expect(result.index).toBe(-1);
    expect(result.isOnBeat).toBe(false);
  });

  it("handles empty beats array", () => {
    const result = getBeatStateAtTime([], 1.0);
    expect(result.index).toBe(-1);
    expect(result.isOnBeat).toBe(false);
    expect(result.intensity).toBe(0);
  });

  it("intensity decays linearly", () => {
    const atBeat = getBeatStateAtTime(beats, 1.0);
    const afterBeat = getBeatStateAtTime(beats, 1.04); // halfway through decay
    expect(atBeat.intensity).toBeGreaterThan(afterBeat.intensity);
    expect(afterBeat.intensity).toBeCloseTo(0.5, 1);
  });
});

// --- interpolateFeature ---

describe("interpolateFeature", () => {
  it("returns 0 for empty arrays", () => {
    expect(interpolateFeature([], [], 5)).toBe(0);
  });

  it("returns first value when target before first time", () => {
    expect(interpolateFeature([1, 2, 3], [10, 20, 30], 0)).toBe(10);
  });

  it("returns last value when target after last time", () => {
    expect(interpolateFeature([1, 2, 3], [10, 20, 30], 5)).toBe(30);
  });

  it("returns exact value at a known time", () => {
    expect(interpolateFeature([0, 1, 2], [0, 0.5, 1.0], 1)).toBe(0.5);
  });

  it("linearly interpolates between two points", () => {
    const result = interpolateFeature([0, 2], [0, 1], 1);
    expect(result).toBeCloseTo(0.5);
  });

  it("interpolates correctly at 25% between points", () => {
    const result = interpolateFeature([0, 4], [0, 100], 1);
    expect(result).toBeCloseTo(25);
  });

  it("handles single element arrays", () => {
    expect(interpolateFeature([5], [42], 5)).toBe(42);
    expect(interpolateFeature([5], [42], 0)).toBe(42);
    expect(interpolateFeature([5], [42], 10)).toBe(42);
  });

  it("handles many points with binary search", () => {
    const times = Array.from({ length: 1000 }, (_, i) => i);
    const values = Array.from({ length: 1000 }, (_, i) => i * 2);

    expect(interpolateFeature(times, values, 500)).toBeCloseTo(1000);
    expect(interpolateFeature(times, values, 250.5)).toBeCloseTo(501);
  });
});

// --- getAudioFeaturesAtTime ---

describe("getAudioFeaturesAtTime", () => {
  it("returns interpolated features for a given time", () => {
    const analysis = {
      spectral: {
        times: [0, 1, 2],
        rms: [0, 0.5, 1],
        spectralCentroid: [100, 200, 300],
        energyBands: {
          bass: [0.8, 0.6, 0.4],
          mid: [0.3, 0.5, 0.7],
          treble: [0.1, 0.2, 0.3],
        },
      },
      harmonicPercussive: {
        harmonicEnergy: [0.5, 0.6, 0.7],
        percussiveEnergy: [0.3, 0.4, 0.5],
      },
    } as unknown as AudioAnalysis;

    const features = getAudioFeaturesAtTime(analysis, 1);
    expect(features.rms).toBeCloseTo(0.5);
    expect(features.spectralCentroid).toBeCloseTo(200);
    expect(features.bass).toBeCloseTo(0.6);
    expect(features.mid).toBeCloseTo(0.5);
    expect(features.treble).toBeCloseTo(0.2);
    expect(features.harmonicEnergy).toBeCloseTo(0.6);
    expect(features.percussiveEnergy).toBeCloseTo(0.4);
  });

  it("interpolates at midpoint between time samples", () => {
    const analysis = {
      spectral: {
        times: [0, 2],
        rms: [0, 1],
        spectralCentroid: [0, 100],
        energyBands: { bass: [0, 1], mid: [0, 1], treble: [0, 1] },
      },
      harmonicPercussive: {
        harmonicEnergy: [0, 1],
        percussiveEnergy: [0, 1],
      },
    } as unknown as AudioAnalysis;

    const features = getAudioFeaturesAtTime(analysis, 1);
    expect(features.rms).toBeCloseTo(0.5);
    expect(features.bass).toBeCloseTo(0.5);
  });
});
