import { ChatPanel } from "@/components/chat/chat-panel";
import { useAnalysisStore } from "@/stores/analysis-store";

export function ChatPage() {
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);

  const showChat = analysis !== null || isAnalyzing;

  return (
    <div className="flex h-full flex-col">
      {showChat && (
        <div className="flex-1 min-h-0">
          <ChatPanel />
        </div>
      )}
    </div>
  );
}
