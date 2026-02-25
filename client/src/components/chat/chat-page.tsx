import { useEffect } from "react";
import { ChatPanel } from "@/components/chat/chat-panel";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useAnalysisStore } from "@/stores/analysis-store";
import { useAudioStore } from "@/stores/audio-store";
import { Music } from "lucide-react";

export function ChatPage() {
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);
  const file = useAudioStore((s) => s.file);

  const showChat = analysis !== null;

  return (
    <div className="flex h-full flex-col items-center">
      {/* Track info header */}
      {file && (
        <div className="flex w-full items-center gap-3 border-b border-border bg-bg-secondary px-6 py-3">
          <Music size={16} className="text-accent" />
          <span className="text-sm text-text-primary font-medium">{file.name}</span>
        </div>
      )}

      <div className="flex w-full flex-1 min-h-0 justify-center">
        {/* Analysis in progress, chat not ready yet */}
        {isAnalyzing && !showChat && (
          <div className="flex items-center justify-center p-8">
            <div className="w-full max-w-md">
              <AnalysisProgress />
            </div>
          </div>
        )}

        {/* Chat interface — centered, max-width container */}
        {showChat && (
          <div className="w-full max-w-2xl flex flex-col min-h-0">
            <ChatPanel />
          </div>
        )}
      </div>
    </div>
  );
}
