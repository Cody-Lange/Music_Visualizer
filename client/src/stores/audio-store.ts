import { create } from "zustand";

export type AppView = "home" | "chat" | "editor";

interface AudioState {
  // File
  file: File | null;
  jobId: string | null;
  audioUrl: string | null;
  audioBuffer: AudioBuffer | null;

  // Navigation
  view: AppView;

  // Playback
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;

  // Actions
  setFile: (file: File, jobId: string) => void;
  setAudioBuffer: (buffer: AudioBuffer) => void;
  setView: (view: AppView) => void;
  setIsPlaying: (playing: boolean) => void;
  setCurrentTime: (time: number) => void;
  setVolume: (volume: number) => void;
  reset: () => void;
}

export const useAudioStore = create<AudioState>((set, get) => ({
  file: null,
  jobId: null,
  audioUrl: null,
  audioBuffer: null,
  view: "home",
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 0.8,

  setFile: (file, jobId) => {
    // Revoke previous URL if any
    const prev = get().audioUrl;
    if (prev) URL.revokeObjectURL(prev);

    const audioUrl = URL.createObjectURL(file);
    set({ file, jobId, audioUrl, currentTime: 0, isPlaying: false });
  },

  setAudioBuffer: (buffer) =>
    set({ audioBuffer: buffer, duration: buffer.duration }),

  setView: (view) => set({ view }),

  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setCurrentTime: (currentTime) => set({ currentTime }),
  setVolume: (volume) => set({ volume: Math.max(0, Math.min(1, volume)) }),

  reset: () => {
    const prev = get().audioUrl;
    if (prev) URL.revokeObjectURL(prev);
    set({
      file: null,
      jobId: null,
      audioUrl: null,
      audioBuffer: null,
      view: "home",
      isPlaying: false,
      currentTime: 0,
      duration: 0,
    });
  },
}));
