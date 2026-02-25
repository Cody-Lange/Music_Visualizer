import { ChatPanel } from "@/components/chat/chat-panel";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useAnalysisStore } from "@/stores/analysis-store";

export function ChatPage() {
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);

  const showChat = analysis !== null;

  return (
    <div className="flex h-full flex-col">
      {/* Analysis checklist — always visible on chat page */}
      {(isAnalyzing || showChat) && (
        <div className="border-b border-border bg-bg-secondary px-6 py-3">
          <AnalysisProgress />
        </div>
      )}

      {/* Waiting state — analysis not yet done, no chat */}
      {isAnalyzing && !showChat && (
        <div className="flex flex-1 items-center justify-center p-8">
          <p className="text-sm text-text-secondary animate-pulse">
            Analyzing your track...
          </p>
        </div>
      )}

      {/* Chat interface — full width */}
      {showChat && (
        <div className="flex-1 min-h-0">
          <ChatPanel />
        </div>
      )}
    </div>
  );
}
