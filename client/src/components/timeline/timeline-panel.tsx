import { useRef, useMemo } from "react";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import { WaveformDisplay } from "@/components/timeline/waveform-display";
import { ZoomIn, ZoomOut } from "lucide-react";
import { useState } from "react";

export function TimelinePanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);

  const duration = useAudioStore((s) => s.duration);
  const currentTime = useAudioStore((s) => s.currentTime);
  const analysis = useAnalysisStore((s) => s.analysis);

  const sections = useMemo(() => {
    if (!analysis) return [];
    const boundaries = analysis.sections.boundaries;
    const labels = analysis.sections.labels;
    return boundaries.map((boundary, i) => ({
      start: boundary,
      end: boundaries[i + 1] ?? duration,
      label: labels[i] ?? `section_${i}`,
    }));
  }, [analysis, duration]);

  const beats = analysis?.rhythm.beats ?? [];

  if (!analysis) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-text-secondary">
        Upload audio to see the timeline
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-bg-primary">
      {/* Controls */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-1.5">
        <span className="text-xs font-medium text-text-secondary">Timeline</span>
        <div className="flex items-center gap-1 ml-auto">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z / 1.5))}
            className="rounded p-1 text-text-secondary hover:bg-bg-tertiary"
          >
            <ZoomOut size={14} />
          </button>
          <span className="w-10 text-center text-xs text-text-secondary tabular-nums">
            {zoom.toFixed(1)}x
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(8, z * 1.5))}
            className="rounded p-1 text-text-secondary hover:bg-bg-tertiary"
          >
            <ZoomIn size={14} />
          </button>
        </div>
      </div>

      {/* Timeline content */}
      <div ref={containerRef} className="flex-1 overflow-x-auto overflow-y-hidden px-2 py-1">
        <div style={{ width: `${Math.max(100, zoom * 100)}%`, minWidth: "100%" }}>
          {/* Waveform + beats */}
          <WaveformDisplay
            rms={analysis.spectral.rms}
            times={analysis.spectral.times}
            beats={beats}
            currentTime={currentTime}
            duration={duration}
            zoom={zoom}
          />

          {/* Section labels */}
          <div className="relative h-6 mt-0.5">
            {sections.map((section, i) => {
              const left = duration > 0 ? (section.start / duration) * 100 : 0;
              const width = duration > 0 ? ((section.end - section.start) / duration) * 100 : 0;

              return (
                <div
                  key={i}
                  className="absolute top-0 h-full border-l border-accent/30 px-1.5"
                  style={{ left: `${left}%`, width: `${width}%` }}
                >
                  <span className="text-[10px] text-accent/70 whitespace-nowrap">
                    {section.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
