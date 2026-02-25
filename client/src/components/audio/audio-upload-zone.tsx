import { useState, useCallback, useRef } from "react";
import { Upload, Music, Loader2 } from "lucide-react";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import { uploadAudio, getAnalysis } from "@/services/api";
import type { AudioAnalysis } from "@/types/audio";

const ACCEPTED_TYPES = [
  "audio/mpeg",
  "audio/wav",
  "audio/flac",
  "audio/ogg",
  "audio/mp4",
  "audio/aac",
  "audio/x-m4a",
];
const MAX_SIZE = 50 * 1024 * 1024;

export function AudioUploadZone() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const setFile = useAudioStore((s) => s.setFile);
  const setView = useAudioStore((s) => s.setView);
  const setAnalysis = useAnalysisStore((s) => s.setAnalysis);
  const setIsAnalyzing = useAnalysisStore((s) => s.setIsAnalyzing);
  const setProgress = useAnalysisStore((s) => s.setProgress);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      // Validate
      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(mp3|wav|flac|ogg|m4a|aac)$/i)) {
        setError("Unsupported format. Accepted: MP3, WAV, FLAC, OGG, M4A, AAC");
        return;
      }
      if (file.size > MAX_SIZE) {
        setError("File too large. Maximum size: 50 MB");
        return;
      }

      setIsUploading(true);
      setIsAnalyzing(true);
      setProgress("uploading", 10, "Uploading audio...");

      // Transition to chat view immediately so user sees progress
      setView("chat");

      try {
        const { job_id } = await uploadAudio(file);
        setFile(file, job_id);
        setProgress("server_analysis", 50, "Analyzing audio...");

        const { analysis } = await getAnalysis(job_id);
        setAnalysis(analysis as AudioAnalysis);
        setProgress("complete", 100, "Analysis complete");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setError(msg);
        setIsAnalyzing(false);
        setView("home");
      } finally {
        setIsUploading(false);
      }
    },
    [setFile, setView, setAnalysis, setIsAnalyzing, setProgress],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center">
          <div className="mb-3 inline-flex rounded-full bg-accent/10 p-3">
            <Music size={32} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold">Music Visualizer</h1>
          <p className="mt-2 text-sm text-text-secondary">
            Drop a track to get started. AI will analyze the music
            and help create a beat-synced visualization video.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition
            ${isDragOver ? "border-accent bg-accent/5" : "border-border hover:border-accent/50 hover:bg-bg-secondary"}
          `}
        >
          {isUploading ? (
            <Loader2 size={36} className="animate-spin text-accent" />
          ) : (
            <Upload size={36} className="text-text-secondary" />
          )}
          <p className="mt-3 text-sm text-text-secondary">
            {isUploading
              ? "Uploading and analyzing..."
              : "Drop your audio file here or click to browse"}
          </p>
          <p className="mt-1 text-xs text-text-secondary/60">
            MP3, WAV, FLAC, OGG, M4A — up to 50 MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.wav,.flac,.ogg,.m4a,.aac,audio/*"
            onChange={onFileChange}
            className="hidden"
          />
        </div>

        {error && (
          <p className="text-center text-sm text-error">{error}</p>
        )}
      </div>
    </div>
  );
}
