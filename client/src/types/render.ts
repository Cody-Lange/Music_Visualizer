export type VisualTemplate =
  | "nebula"
  | "geometric"
  | "waveform"
  | "cinematic"
  | "retro"
  | "nature"
  | "abstract"
  | "urban"
  | "glitchbreak"
  | "90s-anime";

export type MotionStyle =
  | "slow-drift"
  | "pulse"
  | "energetic"
  | "chaotic"
  | "breathing"
  | "glitch"
  | "smooth-flow"
  | "staccato";

export type TransitionType =
  | "fade-from-black"
  | "fade-to-black"
  | "cross-dissolve"
  | "hard-cut"
  | "morph"
  | "flash-white"
  | "wipe"
  | "zoom-in"
  | "zoom-out";

export type LyricsAnimation = "fade-word" | "typewriter" | "karaoke" | "float-up" | "none";

export interface LyricsDisplayConfig {
  enabled: boolean;
  font: "sans" | "serif" | "mono";
  size: "small" | "medium" | "large";
  animation: LyricsAnimation;
  color: string;
  shadow: boolean;
}

export interface SectionSpec {
  label: string;
  startTime: number;
  endTime: number;
  colorPalette: string[];
  motionStyle: MotionStyle;
  intensity: number;
  aiPrompt: string;
  transitionIn: TransitionType;
  transitionOut: TransitionType;
  visualElements: string[];
  keyframeUrl?: string;
}

export interface GlobalStyle {
  template: VisualTemplate;
  styleModifiers: string[];
  recurringMotifs: string[];
  lyricsDisplay: LyricsDisplayConfig;
}

export type AspectRatio = "16:9" | "9:16" | "1:1";
export type VideoQuality = "draft" | "standard" | "high";

export interface ExportSettings {
  resolution: [number, number];
  fps: 24 | 30 | 60;
  aspectRatio: AspectRatio;
  format: "mp4";
  quality: VideoQuality;
}

export interface RenderSpec {
  globalStyle: GlobalStyle;
  sections: SectionSpec[];
  exportSettings: ExportSettings;
}

export type ExportPreset =
  | "youtube"
  | "youtube-hd"
  | "tiktok"
  | "instagram"
  | "twitter"
  | "4k"
  | "custom";

export interface ExportPresetConfig {
  label: string;
  resolution: [number, number];
  aspectRatio: AspectRatio;
  fps: 24 | 30 | 60;
  description: string;
}

export const EXPORT_PRESETS: Record<ExportPreset, ExportPresetConfig> = {
  youtube: {
    label: "YouTube",
    resolution: [1920, 1080],
    aspectRatio: "16:9",
    fps: 30,
    description: "YouTube, Vimeo",
  },
  "youtube-hd": {
    label: "YouTube HD",
    resolution: [1920, 1080],
    aspectRatio: "16:9",
    fps: 60,
    description: "YouTube high frame rate",
  },
  tiktok: {
    label: "TikTok / Reels",
    resolution: [1080, 1920],
    aspectRatio: "9:16",
    fps: 30,
    description: "TikTok, Instagram Reels, Shorts",
  },
  instagram: {
    label: "Instagram Square",
    resolution: [1080, 1080],
    aspectRatio: "1:1",
    fps: 30,
    description: "Instagram Feed",
  },
  twitter: {
    label: "Twitter / X",
    resolution: [1280, 720],
    aspectRatio: "16:9",
    fps: 30,
    description: "Twitter/X video",
  },
  "4k": {
    label: "4K",
    resolution: [3840, 2160],
    aspectRatio: "16:9",
    fps: 30,
    description: "High quality archive",
  },
  custom: {
    label: "Custom",
    resolution: [1920, 1080],
    aspectRatio: "16:9",
    fps: 30,
    description: "User-defined settings",
  },
};
