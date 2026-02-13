import { Music, Upload, Settings } from "lucide-react";
import { useAudioStore } from "@/stores/audio-store";
import { useExportStore } from "@/stores/export-store";
import { EXPORT_PRESETS } from "@/types/render";

export function Header() {
  const file = useAudioStore((s) => s.file);
  const jobId = useAudioStore((s) => s.jobId);
  const reset = useAudioStore((s) => s.reset);
  const activePreset = useExportStore((s) => s.activePreset);

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-bg-secondary px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-accent">
          <Music size={22} />
          <span className="text-lg font-semibold text-text-primary">
            Music Visualizer
          </span>
        </div>

        {file && (
          <span className="ml-4 text-sm text-text-secondary">
            {file.name}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {jobId && (
          <>
            <span className="rounded bg-bg-tertiary px-2 py-1 text-xs text-text-secondary">
              {EXPORT_PRESETS[activePreset]?.label ?? "Custom"}
            </span>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 rounded px-3 py-1.5 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"
            >
              <Upload size={14} />
              New
            </button>
          </>
        )}
        <button className="rounded p-1.5 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary">
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
