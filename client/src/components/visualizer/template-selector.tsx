import { useCallback, useState } from "react";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { useAnalysisStore } from "@/stores/analysis-store";

export function TemplateSelector() {
  const customShaderCode = useVisualizerStore((s) => s.customShaderCode);
  const shaderDescription = useVisualizerStore((s) => s.shaderDescription);
  const setCustomShaderCode = useVisualizerStore((s) => s.setCustomShaderCode);
  const setShaderDescription = useVisualizerStore((s) => s.setShaderDescription);
  const isGeneratingShader = useVisualizerStore((s) => s.isGeneratingShader);
  const setIsGeneratingShader = useVisualizerStore((s) => s.setIsGeneratingShader);
  const shaderError = useVisualizerStore((s) => s.shaderError);
  const setShaderError = useVisualizerStore((s) => s.setShaderError);
  const analysis = useAnalysisStore((s) => s.analysis);

  const [shaderPrompt, setShaderPrompt] = useState("");

  const handleGenerateShader = useCallback(async (description?: string) => {
    const desc = description || shaderPrompt.trim() || shaderDescription || "A mesmerizing audio-reactive visualization";
    const moodTags = analysis?.mood?.tags ?? [];

    setIsGeneratingShader(true);
    setShaderError(null);

    try {
      const res = await fetch("/api/shader/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: desc,
          mood_tags: moodTags,
        }),
      });

      if (!res.ok) {
        throw new Error(`Shader generation failed: HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.shader_code) {
        setCustomShaderCode(data.shader_code);
        setShaderDescription(desc);
        setShaderPrompt("");
      }
    } catch (err) {
      console.error("Shader generation error:", err);
      setShaderError(String(err));
    } finally {
      setIsGeneratingShader(false);
    }
  }, [shaderPrompt, shaderDescription, analysis, setIsGeneratingShader, setShaderError, setCustomShaderCode, setShaderDescription]);

  return (
    <div className="px-3 py-2">
      <label className="mb-1.5 block text-xs font-medium text-text-secondary">
        Shader Visualization
      </label>

      {/* Status indicator */}
      <div className="mb-2 flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${
          isGeneratingShader
            ? "bg-yellow-400 animate-pulse"
            : customShaderCode
              ? "bg-green-400"
              : "bg-text-secondary/30"
        }`} />
        <span className="text-[11px] text-text-secondary">
          {isGeneratingShader
            ? "Generating shader..."
            : customShaderCode
              ? "Custom shader active"
              : "Default shader — describe your vision below"
          }
        </span>
      </div>

      {/* Shader prompt input */}
      <div className="flex gap-1.5">
        <input
          type="text"
          value={shaderPrompt}
          onChange={(e) => setShaderPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !isGeneratingShader) handleGenerateShader();
          }}
          placeholder={shaderDescription || "Raymarched fractals, particle nebula, geometric corridors..."}
          className="flex-1 rounded border border-border bg-bg-tertiary px-2.5 py-1.5 text-xs text-text-primary placeholder:text-text-secondary/40 focus:border-accent focus:outline-none"
        />
        <button
          onClick={() => handleGenerateShader()}
          disabled={isGeneratingShader}
          className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-accent-hover disabled:opacity-40"
        >
          {isGeneratingShader ? "..." : customShaderCode ? "Regenerate" : "Generate"}
        </button>
      </div>

      {/* Error display */}
      {shaderError && (
        <p className="mt-1.5 text-[11px] text-red-400 truncate" title={shaderError}>
          {shaderError}
        </p>
      )}
    </div>
  );
}
