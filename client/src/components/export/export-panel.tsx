import { Download, AlertCircle, Loader2, History } from "lucide-react";
import { useExportStore } from "@/stores/export-store";
import { useRenderStore } from "@/stores/render-store";
import { EXPORT_PRESETS } from "@/types/render";
import type { ExportPreset } from "@/types/render";
import type { RenderHistoryEntry } from "@/stores/render-store";

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
  const renderHistory = useRenderStore((s) => s.renderHistory);

  const isRendering = renderStatus === "queued" || renderStatus === "rendering" || renderStatus === "encoding" || renderStatus === "generating_keyframes";
  const isComplete = renderStatus === "complete";
  const isError = renderStatus === "error";

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
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${percentage}%` }}
              />
            ) : (
              <div className="h-full w-full animate-pulse rounded-full bg-accent/60" />
            )}
          </div>
          <div className="mt-1 flex items-center justify-between">
            <p className="text-xs text-text-secondary">
              <Loader2 size={10} className="mr-1 inline animate-spin" />
              {renderMessage || "Processing..."}
            </p>
            {percentage > 0 && (
              <p className="text-xs font-medium text-accent">{percentage}%</p>
            )}
          </div>
        </div>
      )}

      {/* Download link */}
      {isComplete && downloadUrl && (
        <a
          href={downloadUrl}
          download
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-medium text-white hover:bg-accent-hover"
        >
          <Download size={16} />
          Download MP4
        </a>
      )}

      {/* Render history — persisted in localStorage */}
      {renderHistory.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <History size={11} className="text-text-secondary" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              Previous Renders
            </span>
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {renderHistory.map((entry: RenderHistoryEntry) => (
              <a
                key={entry.renderId}
                href={entry.downloadUrl}
                download
                className="flex items-center justify-between rounded px-2 py-1 text-xs text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition"
              >
                <span>{new Date(entry.timestamp).toLocaleString()}</span>
                <Download size={11} />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
