import { useVisualizerStore } from "@/stores/visualizer-store";
import type { VisualTemplate } from "@/types/render";

const TEMPLATES: { key: VisualTemplate; label: string; emoji: string }[] = [
  { key: "nebula", label: "Nebula", emoji: "N" },
  { key: "geometric", label: "Geometric", emoji: "G" },
  { key: "waveform", label: "Waveform", emoji: "W" },
  { key: "cinematic", label: "Cinematic", emoji: "C" },
  { key: "retro", label: "Retro", emoji: "R" },
  { key: "nature", label: "Nature", emoji: "F" },
  { key: "abstract", label: "Abstract", emoji: "A" },
  { key: "urban", label: "Urban", emoji: "U" },
];

export function TemplateSelector() {
  const activeTemplate = useVisualizerStore((s) => s.activeTemplate);
  const setActiveTemplate = useVisualizerStore((s) => s.setActiveTemplate);

  return (
    <div className="px-3 py-2">
      <label className="mb-1.5 block text-xs font-medium text-text-secondary">
        Visual Template
      </label>
      <div className="flex flex-wrap gap-1.5">
        {TEMPLATES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTemplate(key)}
            className={`rounded px-2 py-1 text-xs transition ${
              activeTemplate === key
                ? "bg-accent text-white"
                : "bg-bg-tertiary text-text-secondary hover:text-text-primary"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
