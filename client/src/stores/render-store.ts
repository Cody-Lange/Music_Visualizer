import { create } from "zustand";
import type { RenderStatus } from "@/types/chat";

interface ProgressDetails {
  currentFrame?: number;
  totalFrames?: number;
  elapsedSeconds?: number;
  estimatedRemaining?: number | null;
  previewUrl?: string | null;
}

interface RenderState {
  renderId: string | null;
  status: RenderStatus;
  percentage: number;
  message: string;
  downloadUrl: string | null;
  error: string | null;

  // Extended progress fields
  currentFrame: number;
  totalFrames: number;
  elapsedSeconds: number;
  estimatedRemaining: number | null;
  previewUrl: string | null;

  setRenderId: (id: string) => void;
  setStatus: (status: RenderStatus) => void;
  setProgress: (percentage: number, message: string) => void;
  setProgressDetails: (details: ProgressDetails) => void;
  setDownloadUrl: (url: string) => void;
  setError: (error: string) => void;
  reset: () => void;
}

export const useRenderStore = create<RenderState>((set) => ({
  renderId: null,
  status: "idle",
  percentage: 0,
  message: "",
  downloadUrl: null,
  error: null,

  // Extended progress fields
  currentFrame: 0,
  totalFrames: 0,
  elapsedSeconds: 0,
  estimatedRemaining: null,
  previewUrl: null,

  setRenderId: (renderId) => set({ renderId }),
  setStatus: (status) => set({ status }),
  setProgress: (percentage, message) => set({ percentage, message }),
  setProgressDetails: (details) =>
    set({
      currentFrame: details.currentFrame ?? 0,
      totalFrames: details.totalFrames ?? 0,
      elapsedSeconds: details.elapsedSeconds ?? 0,
      estimatedRemaining: details.estimatedRemaining ?? null,
      previewUrl: details.previewUrl ?? null,
    }),
  setDownloadUrl: (downloadUrl) =>
    set({ downloadUrl, status: "complete", percentage: 100 }),
  setError: (error) => set({ error, status: "error" }),

  reset: () =>
    set({
      renderId: null,
      status: "idle",
      percentage: 0,
      message: "",
      downloadUrl: null,
      error: null,
      currentFrame: 0,
      totalFrames: 0,
      elapsedSeconds: 0,
      estimatedRemaining: null,
      previewUrl: null,
    }),
}));
