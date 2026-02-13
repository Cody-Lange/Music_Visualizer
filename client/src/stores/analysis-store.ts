import { create } from "zustand";
import type { AudioAnalysis } from "@/types/audio";
import type { LyricsData } from "@/types/lyrics";
import type { AnalysisStep } from "@/types/chat";

interface AnalysisState {
  analysis: AudioAnalysis | null;
  lyrics: LyricsData | null;
  analysisStep: AnalysisStep;
  analysisProgress: number;
  analysisMessage: string;
  isAnalyzing: boolean;

  setAnalysis: (analysis: AudioAnalysis) => void;
  setLyrics: (lyrics: LyricsData) => void;
  setProgress: (step: AnalysisStep, progress: number, message: string) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  analysis: null,
  lyrics: null,
  analysisStep: "uploading",
  analysisProgress: 0,
  analysisMessage: "",
  isAnalyzing: false,

  setAnalysis: (analysis) => set({ analysis }),
  setLyrics: (lyrics) => set({ lyrics }),
  setProgress: (step, progress, message) =>
    set({
      analysisStep: step,
      analysisProgress: progress,
      analysisMessage: message,
    }),
  setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing }),

  reset: () =>
    set({
      analysis: null,
      lyrics: null,
      analysisStep: "uploading",
      analysisProgress: 0,
      analysisMessage: "",
      isAnalyzing: false,
    }),
}));
