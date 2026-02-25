import { useCallback, useState } from "react";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import type { VisualTemplate } from "@/types/render";

const TEMPLATES: { key: VisualTemplate; label: string }[] = [
  { key: "nebula", label: "Nebula" },
  { key: "geometric", label: "Geometric" },
  { key: "waveform", label: "Waveform" },
  { key: "cinematic", label: "Cinematic" },
  { key: "retro", label: "Retro" },
  { key: "nature", label: "Nature" },
  { key: "abstract", label: "Abstract" },
  { key: "urban", label: "Urban" },
  { key: "glitchbreak", label: "Glitchbreak" },
  { key: "90s-anime", label: "90s Anime" },
];

export function TemplateSelector() {
  const activeTemplate = useVisualizerStore((s) => s.activeTemplate);
  const setActiveTemplate = useVisualizerStore((s) => s.setActiveTemplate);
  const customShaderCode = useVisualizerStore((s) => s.customShaderCode);
  const setCustomShaderCode = useVisualizerStore((s) => s.setCustomShaderCode);
  const isGeneratingShader = useVisualizerStore((s) => s.isGeneratingShader);
  const setIsGeneratingShader = useVisualizerStore((s) => s.setIsGeneratingShader);
  const setShaderError = useVisualizerStore((s) => s.setShaderError);
  const analysis = useAnalysisStore((s) => s.analysis);

  const [shaderPrompt, setShaderPrompt] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);

  const handleGenerateShader = useCallback(async () => {
    const description = shaderPrompt.trim() || `A ${activeTemplate}-style music visualization`;
    const moodTags = analysis?.mood?.tags ?? [];

    setIsGeneratingShader(true);
    setShaderError(null);

    try {
      const res = await fetch("/api/shader/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description,
          template: activeTemplate,
          mood_tags: moodTags,
        }),
      });

      if (!res.ok) {
        throw new Error(`Shader generation failed: HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.shader_code) {
        setCustomShaderCode(data.shader_code);
        setShowPrompt(false);
        setShaderPrompt("");
      }
    } catch (err) {
      console.error("Shader generation error:", err);
      setShaderError(String(err));
    } finally {
      setIsGeneratingShader(false);
    }
  }, [shaderPrompt, activeTemplate, analysis, setIsGeneratingShader, setShaderError, setCustomShaderCode]);

  const handleClearShader = useCallback(() => {
    setCustomShaderCode(null);
    setShaderError(null);
  }, [setCustomShaderCode, setShaderError]);

  const handleTemplateClick = useCallback(
    (key: VisualTemplate) => {
      setActiveTemplate(key);
      // Switch back to built-in template, clearing custom shader
      if (customShaderCode) {
        setCustomShaderCode(null);
      }
    },
    [setActiveTemplate, customShaderCode, setCustomShaderCode],
  );

  return (
    <div className="px-3 py-2">
      <label className="mb-1.5 block text-xs font-medium text-text-secondary">
        Visual Template
      </label>
      <div className="flex flex-wrap gap-1.5">
        {TEMPLATES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => handleTemplateClick(key)}
            className={`rounded px-2 py-1 text-xs transition ${
              activeTemplate === key && !customShaderCode
                ? "bg-accent text-white"
                : "bg-bg-tertiary text-text-secondary hover:text-text-primary"
            }`}
          >
            {label}
          </button>
        ))}

        {/* AI Shader button */}
        <button
          onClick={() => {
            if (customShaderCode) {
              handleClearShader();
            } else {
              setShowPrompt(!showPrompt);
            }
          }}
          disabled={isGeneratingShader}
          className={`rounded px-2 py-1 text-xs transition ${
            customShaderCode
              ? "bg-purple-600 text-white"
              : showPrompt
                ? "bg-purple-600/20 text-purple-400 ring-1 ring-purple-500"
                : "bg-purple-600/10 text-purple-400 hover:bg-purple-600/20"
          }`}
        >
          {isGeneratingShader ? "Generating..." : customShaderCode ? "AI Shader (Clear)" : "AI Shader"}
        </button>
      </div>

      {/* Shader prompt input */}
      {showPrompt && !customShaderCode && (
        <div className="mt-2 flex gap-1.5">
          <input
            type="text"
            value={shaderPrompt}
            onChange={(e) => setShaderPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !isGeneratingShader) handleGenerateShader();
            }}
            placeholder="Describe the shader (or leave empty for auto)..."
            className="flex-1 rounded border border-border bg-bg-tertiary px-2.5 py-1.5 text-xs text-text-primary placeholder:text-text-secondary/40 focus:border-purple-500 focus:outline-none"
          />
          <button
            onClick={handleGenerateShader}
            disabled={isGeneratingShader}
            className="rounded bg-purple-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-purple-700 disabled:opacity-40"
          >
            {isGeneratingShader ? "..." : "Generate"}
          </button>
        </div>
      )}
    </div>
  );
}
