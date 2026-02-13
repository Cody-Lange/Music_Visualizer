import { create } from "zustand";
import type { ExportPreset, ExportSettings, AspectRatio } from "@/types/render";
import { EXPORT_PRESETS } from "@/types/render";

interface ExportState {
  activePreset: ExportPreset;
  settings: ExportSettings;

  setPreset: (preset: ExportPreset) => void;
  setResolution: (resolution: [number, number]) => void;
  setFps: (fps: 24 | 30 | 60) => void;
  setAspectRatio: (ratio: AspectRatio) => void;
  reset: () => void;
}

export const useExportStore = create<ExportState>((set) => ({
  activePreset: "youtube",
  settings: {
    resolution: [1920, 1080],
    fps: 30,
    aspectRatio: "16:9",
    format: "mp4",
    quality: "high",
  },

  setPreset: (preset) => {
    const config = EXPORT_PRESETS[preset];
    if (!config) return;
    set({
      activePreset: preset,
      settings: {
        resolution: config.resolution,
        fps: config.fps,
        aspectRatio: config.aspectRatio,
        format: "mp4",
        quality: "high",
      },
    });
  },

  setResolution: (resolution) =>
    set((state) => ({
      activePreset: "custom",
      settings: { ...state.settings, resolution },
    })),

  setFps: (fps) =>
    set((state) => ({
      settings: { ...state.settings, fps },
    })),

  setAspectRatio: (aspectRatio) =>
    set((state) => ({
      settings: { ...state.settings, aspectRatio },
    })),

  reset: () =>
    set({
      activePreset: "youtube",
      settings: {
        resolution: [1920, 1080],
        fps: 30,
        aspectRatio: "16:9",
        format: "mp4",
        quality: "high",
      },
    }),
}));
