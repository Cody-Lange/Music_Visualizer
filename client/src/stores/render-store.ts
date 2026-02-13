import { create } from "zustand";
import type { RenderStatus } from "@/types/chat";

interface RenderState {
  renderId: string | null;
  status: RenderStatus;
  percentage: number;
  message: string;
  downloadUrl: string | null;
  error: string | null;

  setRenderId: (id: string) => void;
  setStatus: (status: RenderStatus) => void;
  setProgress: (percentage: number, message: string) => void;
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

  setRenderId: (renderId) => set({ renderId }),
  setStatus: (status) => set({ status }),
  setProgress: (percentage, message) => set({ percentage, message }),
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
    }),
}));
