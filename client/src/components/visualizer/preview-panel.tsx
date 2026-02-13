import { AudioPlayer } from "@/components/audio/audio-player";
import { VisualizerCanvas } from "@/components/visualizer/visualizer-canvas";
import { TemplateSelector } from "@/components/visualizer/template-selector";
import { ExportPanel } from "@/components/export/export-panel";
import { useRenderStore } from "@/stores/render-store";

export function PreviewPanel() {
  const downloadUrl = useRenderStore((s) => s.downloadUrl);

  return (
    <div className="flex h-full flex-col">
      {/* Visualizer */}
      <div className="relative flex-1 bg-black">
        {downloadUrl ? (
          <video
            src={downloadUrl}
            controls
            className="h-full w-full object-contain"
          />
        ) : (
          <VisualizerCanvas />
        )}
      </div>

      {/* Audio controls */}
      <div className="border-t border-border bg-bg-secondary">
        <AudioPlayer />
      </div>

      {/* Template selector + Export */}
      <div className="border-t border-border bg-bg-secondary">
        <TemplateSelector />
        <ExportPanel />
      </div>
    </div>
  );
}
