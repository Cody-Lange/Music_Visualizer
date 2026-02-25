import { create } from "zustand";
import type { VisualTemplate } from "@/types/render";

interface VisualizerState {
  activeTemplate: VisualTemplate;
  isPreviewPlaying: boolean;
  customShaderCode: string | null;
  shaderError: string | null;
  isGeneratingShader: boolean;

  setActiveTemplate: (template: VisualTemplate) => void;
  setIsPreviewPlaying: (playing: boolean) => void;
  setCustomShaderCode: (code: string | null) => void;
  setShaderError: (error: string | null) => void;
  setIsGeneratingShader: (generating: boolean) => void;
  reset: () => void;
}

export const useVisualizerStore = create<VisualizerState>((set) => ({
  activeTemplate: "nebula",
  isPreviewPlaying: false,
  customShaderCode: null,
  shaderError: null,
  isGeneratingShader: false,

  setActiveTemplate: (activeTemplate) => set({ activeTemplate }),
  setIsPreviewPlaying: (isPreviewPlaying) => set({ isPreviewPlaying }),
  setCustomShaderCode: (customShaderCode) => set({ customShaderCode, shaderError: null }),
  setShaderError: (shaderError) => set({ shaderError }),
  setIsGeneratingShader: (isGeneratingShader) => set({ isGeneratingShader }),

  reset: () =>
    set({
      activeTemplate: "nebula",
      isPreviewPlaying: false,
      customShaderCode: null,
      shaderError: null,
      isGeneratingShader: false,
    }),
}));
