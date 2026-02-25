import { create } from "zustand";

interface VisualizerState {
  customShaderCode: string | null;
  shaderDescription: string | null;
  shaderError: string | null;
  isGeneratingShader: boolean;
  isPreviewPlaying: boolean;

  setCustomShaderCode: (code: string | null) => void;
  setShaderDescription: (desc: string | null) => void;
  setShaderError: (error: string | null) => void;
  setIsGeneratingShader: (generating: boolean) => void;
  setIsPreviewPlaying: (playing: boolean) => void;
  reset: () => void;
}

export const useVisualizerStore = create<VisualizerState>((set) => ({
  customShaderCode: null,
  shaderDescription: null,
  shaderError: null,
  isGeneratingShader: false,
  isPreviewPlaying: false,

  setCustomShaderCode: (customShaderCode) => set({ customShaderCode, shaderError: null }),
  setShaderDescription: (shaderDescription) => set({ shaderDescription }),
  setShaderError: (shaderError) => set({ shaderError }),
  setIsGeneratingShader: (isGeneratingShader) => set({ isGeneratingShader }),
  setIsPreviewPlaying: (isPreviewPlaying) => set({ isPreviewPlaying }),

  reset: () =>
    set({
      customShaderCode: null,
      shaderDescription: null,
      shaderError: null,
      isGeneratingShader: false,
      isPreviewPlaying: false,
    }),
}));
