import { Download, Loader2, AlertCircle, RotateCcw } from "lucide-react";
import { useExportStore } from "@/stores/export-store";
import { useRenderStore } from "@/stores/render-store";
import { useAudioStore } from "@/stores/audio-store";
import { useChatStore } from "@/stores/chat-store";
import { startRender, getRenderStatus } from "@/services/api";
import { EXPORT_PRESETS } from "@/types/render";
import type { ExportPreset } from "@/types/render";

const PRESET_KEYS: ExportPreset[] = [
  "youtube",
  "youtube-hd",
  "tiktok",
  "instagram",
  "twitter",
  "4k",
];

export function ExportPanel() {
  const activePreset = useExportStore((s) => s.activePreset);
  const exportSettings = useExportStore((s) => s.settings);
  const setPreset = useExportStore((s) => s.setPreset);

  const renderStatus = useRenderStore((s) => s.status);
  const percentage = useRenderStore((s) => s.percentage);
  const renderMessage = useRenderStore((s) => s.message);
  const downloadUrl = useRenderStore((s) => s.downloadUrl);
  const renderError = useRenderStore((s) => s.error);
  const setRenderId = useRenderStore((s) => s.setRenderId);
  const setStatus = useRenderStore((s) => s.setStatus);
  const setProgress = useRenderStore((s) => s.setProgress);
  const setDownloadUrl = useRenderStore((s) => s.setDownloadUrl);
  const setError = useRenderStore((s) => s.setError);
  const resetRender = useRenderStore((s) => s.reset);

  const jobId = useAudioStore((s) => s.jobId);
  const renderSpec = useChatStore((s) => s.renderSpec);

  const isRendering = renderStatus === "queued" || renderStatus === "rendering" || renderStatus === "encoding" || renderStatus === "generating_keyframes";
  const isComplete = renderStatus === "complete";
  const isError = renderStatus === "error";

  const handleRender = async () => {
    if (!jobId) return;

    const spec = renderSpec ?? {
      global_style: { template: "nebula", style_modifiers: [], recurring_motifs: [], lyrics_display: { enabled: true, font: "sans", size: "medium", animation: "fade-word", color: "#F0F0F5", shadow: true } },
      sections: [],
      export_settings: {
        resolution: exportSettings.resolution,
        fps: exportSettings.fps,
        aspect_ratio: exportSettings.aspectRatio,
        format: "mp4",
        quality: exportSettings.quality,
      },
    };

    resetRender();
    setStatus("queued");
    setProgress(0, "Starting render...");

    try {
      const result = await startRender(jobId, spec);
      setRenderId(result.render_id);

      // The render endpoint is synchronous — by the time we get the response,
      // the job is already complete or errored. Check status once.
      const status = await getRenderStatus(result.render_id);
      setProgress(status.percentage, status.percentage === 100 ? "Complete!" : `Rendering... ${status.percentage}%`);

      if (status.status === "complete" && status.download_url) {
        setDownloadUrl(status.download_url);
      } else if (status.status === "error") {
        setError(status.error ?? "Render failed");
      } else if (status.download_url) {
        setDownloadUrl(status.download_url);
      } else {
        setError("Render completed but no download URL was returned.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Render failed");
    }
  };

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Export
      </h3>

      {/* Preset selector */}
      <div className="flex flex-wrap gap-1.5">
        {PRESET_KEYS.map((key) => {
          const preset = EXPORT_PRESETS[key]!;
          return (
            <button
              key={key}
              onClick={() => setPreset(key)}
              className={`rounded px-2 py-1 text-xs transition ${
                activePreset === key
                  ? "bg-accent text-white"
                  : "bg-bg-tertiary text-text-secondary hover:text-text-primary"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Current settings display */}
      <div className="text-xs text-text-secondary">
        {exportSettings.resolution[0]}x{exportSettings.resolution[1]} &middot;{" "}
        {exportSettings.fps}fps &middot; {exportSettings.aspectRatio}
      </div>

      {/* Error display */}
      {isError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle size={14} className="mt-0.5 shrink-0 text-red-400" />
            <div className="min-w-0">
              <p className="text-xs font-medium text-red-400">Render failed</p>
              <p className="mt-0.5 text-xs text-red-400/70 break-words">
                {renderError}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Progress bar during rendering */}
      {isRendering && (
        <div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg-tertiary">
            {percentage > 0 ? (
              <div
                className="h-full rounded-full bg-accent transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            ) : (
              <div className="h-full w-full animate-pulse rounded-full bg-accent/60" />
            )}
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {renderMessage || "Processing..."}
          </p>
        </div>
      )}

      {/* Render / Retry button */}
      <button
        onClick={isError ? () => { resetRender(); handleRender(); } : handleRender}
        disabled={isRendering || !jobId}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
      >
        {isRendering ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Rendering...
          </>
        ) : isError ? (
          <>
            <RotateCcw size={16} />
            Retry Render
          </>
        ) : (
          <>Render Video</>
        )}
      </button>

      {/* Download link */}
      {isComplete && downloadUrl && (
        <a
          href={downloadUrl}
          download
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-accent py-2 text-sm text-accent hover:bg-accent/10"
        >
          <Download size={16} />
          Download MP4
        </a>
      )}
    </div>
  );
}
