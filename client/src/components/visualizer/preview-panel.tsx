import { AudioPlayer } from "@/components/audio/audio-player";
import { VisualizerCanvas } from "@/components/visualizer/visualizer-canvas";
import { TemplateSelector } from "@/components/visualizer/template-selector";
import { ExportPanel } from "@/components/export/export-panel";
import { useRenderStore } from "@/stores/render-store";

export function PreviewPanel() {
  const downloadUrl = useRenderStore((s) => s.downloadUrl);

  return (
    <div className="flex h-full flex-col">
      {/* Visualizer / Rendered video */}
      <div
        className={`relative bg-black ${
          downloadUrl
            ? "flex-shrink-0 flex items-center justify-center"
            : "flex-1"
        }`}
        style={downloadUrl ? { height: "clamp(200px, 40vh, 420px)" } : undefined}
      >
        {downloadUrl ? (
          <video
            src={downloadUrl}
            controls
            autoPlay
            className="max-h-full max-w-full rounded object-contain"
          />
        ) : (
          <VisualizerCanvas />
        )}
      </div>

      {/* Audio controls */}
      <div className="border-t border-border bg-bg-secondary">
        <AudioPlayer />
      </div>

      {/* Template selector + Export — expands to fill remaining space when video is constrained */}
      <div
        className={`border-t border-border bg-bg-secondary ${
          downloadUrl ? "flex-1 overflow-y-auto" : ""
        }`}
      >
        <TemplateSelector />
        <ExportPanel />
      </div>
    </div>
  );
}
