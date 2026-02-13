export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export type AnalysisStep =
  | "uploading"
  | "client_analysis"
  | "server_analysis"
  | "vocal_separation"
  | "lyrics_transcription"
  | "lyrics_fetch"
  | "thematic_analysis"
  | "complete";

export interface AnalysisProgress {
  step: AnalysisStep;
  progress: number;
  message: string;
}

export type RenderStatus = "idle" | "queued" | "generating_keyframes" | "rendering" | "encoding" | "complete" | "error";

export interface RenderProgress {
  status: RenderStatus;
  currentFrame?: number;
  totalFrames?: number;
  percentage: number;
  message: string;
  downloadUrl?: string;
  error?: string;
}
