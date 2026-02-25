import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, CheckCircle2, Sparkles, MessageSquare, Clapperboard } from "lucide-react";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import { ChatMessage } from "@/components/chat/chat-message";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import type { ChatPhase } from "@/services/websocket";

const PHASE_CONFIG: Record<ChatPhase, { label: string; description: string; icon: typeof Sparkles }> = {
  analysis: {
    label: "Analyzing",
    description: "Generating thematic analysis and visualization suggestions...",
    icon: Sparkles,
  },
  refinement: {
    label: "Refining",
    description: "Discuss and refine the visualization plan",
    icon: MessageSquare,
  },
  confirmation: {
    label: "Ready to Render",
    description: "Confirm the plan to start rendering",
    icon: CheckCircle2,
  },
  rendering: {
    label: "Rendering",
    description: "Render spec generated — ready to produce video",
    icon: Clapperboard,
  },
  editing: {
    label: "Editing",
    description: "Request changes to the rendered video",
    icon: MessageSquare,
  },
};

function PhaseIndicator({ phase }: { phase: ChatPhase }) {
  const config = PHASE_CONFIG[phase];
  const Icon = config.icon;
  return (
    <div className="flex items-center gap-2">
      <Icon size={14} className="text-accent" />
      <span className="text-xs font-medium text-accent">{config.label}</span>
      <span className="text-xs text-text-secondary">— {config.description}</span>
    </div>
  );
}

function getPlaceholder(phase: ChatPhase, hasAnalysis: boolean): string {
  if (!hasAnalysis) return "Waiting for analysis...";
  switch (phase) {
    case "analysis":
      return "Describe your vision for the visualization...";
    case "refinement":
      return "Describe changes or ask questions...";
    case "confirmation":
      return "Confirm to render, or request more changes...";
    case "rendering":
      return "Video is being prepared...";
    case "editing":
      return "Describe what you'd like to change...";
  }
}

export function ChatPanel() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const addMessage = useChatStore((s) => s.addMessage);
  const phase = useChatStore((s) => s.phase);
  const renderSpec = useChatStore((s) => s.renderSpec);

  const jobId = useAudioStore((s) => s.jobId);
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysis = useAnalysisStore((s) => s.analysis);

  const { sendMessage, isConnected } = useChatWebSocket();

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  // When analysis completes and there's already a user message, trigger the LLM
  useEffect(() => {
    if (analysis && messages.length === 1 && messages[0]?.role === "user" && isConnected) {
      sendMessage(messages[0].content);
    }
    // Only run when analysis first completes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis, isConnected]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isStreaming) return;

    addMessage({
      id: createMessageId(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    });

    sendMessage(text);
    setInput("");
  }, [input, isStreaming, addMessage, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = analysis && !isStreaming && phase !== "rendering";

  return (
    <div className="flex h-full flex-col bg-bg-secondary">
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Creative Director</h2>
        <p className="text-xs text-text-secondary">
          {jobId
            ? "Discuss visualization ideas for your track"
            : "Upload a track to get started"}
        </p>
        {jobId && analysis && (
          <div className="mt-1">
            <PhaseIndicator phase={phase} />
          </div>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {isAnalyzing && <AnalysisProgress />}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {renderSpec && phase === "rendering" && (
          <div className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-xs text-text-secondary">
            <div className="flex items-center gap-2 mb-1">
              <Clapperboard size={14} className="text-accent" />
              <span className="font-medium text-text-primary">Render spec ready</span>
            </div>
            <p>
              Template: {(renderSpec as any).global_style?.template ?? (renderSpec as any).globalStyle?.template ?? "—"} | Sections: {(renderSpec as any).sections?.length ?? 0}
            </p>
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <Loader2 size={12} className="animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={getPlaceholder(phase, !!analysis)}
            disabled={!canSend}
            rows={2}
            className="flex-1 resize-none rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 focus:border-accent focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !canSend}
            className="flex h-10 w-10 items-center justify-center self-end rounded-lg bg-accent text-white hover:bg-accent-hover disabled:opacity-40"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
