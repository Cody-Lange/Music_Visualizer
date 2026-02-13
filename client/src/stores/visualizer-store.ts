import { create } from "zustand";
import type { VisualTemplate } from "@/types/render";

interface VisualizerState {
  activeTemplate: VisualTemplate;
  isPreviewPlaying: boolean;

  setActiveTemplate: (template: VisualTemplate) => void;
  setIsPreviewPlaying: (playing: boolean) => void;
  reset: () => void;
}

export const useVisualizerStore = create<VisualizerState>((set) => ({
  activeTemplate: "nebula",
  isPreviewPlaying: false,

  setActiveTemplate: (activeTemplate) => set({ activeTemplate }),
  setIsPreviewPlaying: (isPreviewPlaying) => set({ isPreviewPlaying }),

  reset: () =>
    set({
      activeTemplate: "nebula",
      isPreviewPlaying: false,
    }),
}));
