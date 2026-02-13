export type LyricsSource = "genius" | "musixmatch" | "whisper" | "manual" | "merged";

export interface LyricsWord {
  text: string;
  startTime: number;
  endTime: number;
  confidence: number;
  lineIndex: number;
}

export interface LyricsLine {
  text: string;
  startTime: number;
  endTime: number;
  words: LyricsWord[];
}

export interface LyricsMetadata {
  title?: string;
  artist?: string;
  album?: string;
  geniusUrl?: string;
  hasSync: boolean;
}

export interface LyricsData {
  source: LyricsSource;
  language: string;
  confidence: number;
  lines: LyricsLine[];
  words: LyricsWord[];
  metadata: LyricsMetadata;
}
