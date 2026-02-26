import { create } from "zustand";
import type { RenderStatus } from "@/types/chat";

interface ProgressDetails {
  currentFrame?: number;
  totalFrames?: number;
  elapsedSeconds?: number;
  estimatedRemaining?: number | null;
  previewUrl?: string | null;
}

export interface RenderHistoryEntry {
  renderId: string;
  downloadUrl: string;
  timestamp: number;
}

const HISTORY_KEY = "mv_render_history";
const MAX_HISTORY = 20;

function loadHistory(): RenderHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RenderHistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(entries: RenderHistoryEntry[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)));
  } catch {
    // localStorage full or unavailable — ignore
  }
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

  // Persisted render history (survives browser crashes / refreshes)
  renderHistory: RenderHistoryEntry[];

  setRenderId: (id: string) => void;
  setStatus: (status: RenderStatus) => void;
  setProgress: (percentage: number, message: string) => void;
  setProgressDetails: (details: ProgressDetails) => void;
  setDownloadUrl: (url: string) => void;
  setError: (error: string) => void;
  clearHistory: () => void;
  reset: () => void;
}

export const useRenderStore = create<RenderState>((set, get) => ({
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

  renderHistory: loadHistory(),

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
  setDownloadUrl: (downloadUrl) => {
    const { renderId, renderHistory } = get();
    // Persist to localStorage so the render survives browser crashes
    if (renderId && downloadUrl) {
      const entry: RenderHistoryEntry = {
        renderId,
        downloadUrl,
        timestamp: Date.now(),
      };
      const updated = [entry, ...renderHistory.filter((e) => e.renderId !== renderId)];
      saveHistory(updated);
      set({ downloadUrl, status: "complete", percentage: 100, renderHistory: updated });
    } else {
      set({ downloadUrl, status: "complete", percentage: 100 });
    }
  },
  setError: (error) => set({ error, status: "error" }),

  clearHistory: () => {
    saveHistory([]);
    set({ renderHistory: [] });
  },

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
      // Keep renderHistory — don't clear on reset
    }),
}));
