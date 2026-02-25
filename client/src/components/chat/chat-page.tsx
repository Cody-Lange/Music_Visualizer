import { ChatPanel } from "@/components/chat/chat-panel";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useAnalysisStore } from "@/stores/analysis-store";

export function ChatPage() {
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);

  const showChat = analysis !== null;

  return (
    <div className="flex h-full flex-col items-center">
      <div className="flex w-full flex-1 min-h-0 justify-center">
        {/* Analysis in progress, chat not ready yet */}
        {isAnalyzing && !showChat && (
          <div className="flex items-center justify-center p-8">
            <div className="w-full max-w-md">
              <AnalysisProgress />
            </div>
          </div>
        )}

        {/* Chat interface — centered, comfortable width */}
        {showChat && (
          <div className="w-full max-w-3xl flex flex-col min-h-0">
            <ChatPanel />
          </div>
        )}
      </div>
    </div>
  );
}
