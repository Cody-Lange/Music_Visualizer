import { CheckCircle, Circle, Loader2 } from "lucide-react";
import { useAnalysisStore } from "@/stores/analysis-store";
import type { AnalysisStep } from "@/types/chat";

const STEPS: { key: AnalysisStep; label: string }[] = [
  { key: "uploading", label: "Uploading audio" },
  { key: "server_analysis", label: "Analyzing audio features" },
  { key: "lyrics_fetch", label: "Fetching lyrics" },
  { key: "thematic_analysis", label: "Generating thematic analysis" },
  { key: "complete", label: "Analysis complete" },
];

export function AnalysisProgress() {
  const currentStep = useAnalysisStore((s) => s.analysisStep);

  const stepIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <div className="rounded-lg border border-border bg-bg-primary p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Analysis Progress
      </h3>
      <div className="space-y-2.5">
        {STEPS.map((step, i) => {
          const isComplete = i < stepIndex || currentStep === "complete";
          const isCurrent = i === stepIndex && currentStep !== "complete";

          return (
            <div key={step.key} className="flex items-center gap-2.5">
              {isComplete ? (
                <CheckCircle size={14} className="text-success" />
              ) : isCurrent ? (
                <Loader2 size={14} className="animate-spin text-accent" />
              ) : (
                <Circle size={14} className="text-text-secondary/30" />
              )}
              <span
                className={`text-sm ${
                  isComplete
                    ? "text-text-secondary"
                    : isCurrent
                      ? "text-text-primary"
                      : "text-text-secondary/40"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
