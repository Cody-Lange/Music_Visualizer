import { ChatPanel } from "@/components/chat/chat-panel";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useAnalysisStore } from "@/stores/analysis-store";

export function ChatPage() {
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);

  const showChat = analysis !== null;

  return (
    <div className="flex h-full flex-col">
      {/* Analysis in progress, chat not ready yet */}
      {isAnalyzing && !showChat && (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="w-full max-w-md">
            <AnalysisProgress />
          </div>
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
