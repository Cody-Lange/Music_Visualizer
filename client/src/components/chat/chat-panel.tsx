import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, CheckCircle2, Sparkles, MessageSquare, Clapperboard } from "lucide-react";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import { useRenderStore } from "@/stores/render-store";
import { ChatMessage } from "@/components/chat/chat-message";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useChatWs } from "@/providers/chat-ws-provider";
import type { ChatPhase } from "@/services/websocket";

const PHASE_CONFIG: Record<ChatPhase, { label: string; icon: typeof Sparkles; color: string }> = {
  analysis: {
    label: "Analyzing",
    icon: Sparkles,
    color: "text-accent",
  },
  refinement: {
    label: "Refining",
    icon: MessageSquare,
    color: "text-accent",
  },
  confirmation: {
    label: "Ready to Render",
    icon: CheckCircle2,
    color: "text-success",
  },
  rendering: {
    label: "Rendering",
    icon: Clapperboard,
    color: "text-warning",
  },
  editing: {
    label: "Editing",
    icon: MessageSquare,
    color: "text-accent",
  },
};

function PhaseIndicator({ phase }: { phase: ChatPhase }) {
  const config = PHASE_CONFIG[phase];
  const Icon = config.icon;
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full bg-bg-tertiary px-2.5 py-1 ${config.color}`}>
      <Icon size={12} />
      <span className="text-[11px] font-medium">{config.label}</span>
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
      return "Rendering in progress. You'll be taken to the editor shortly...";
    case "editing":
      return "Describe what you'd like to change...";
  }
}

export function ChatPanel() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const renderTriggered = useRef(false);

  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const addMessage = useChatStore((s) => s.addMessage);
  const phase = useChatStore((s) => s.phase);
  const renderSpec = useChatStore((s) => s.renderSpec);
  const initialAnalysisSent = useChatStore((s) => s.initialAnalysisSent);
  const setInitialAnalysisSent = useChatStore((s) => s.setInitialAnalysisSent);

  const setView = useAudioStore((s) => s.setView);
  const jobId = useAudioStore((s) => s.jobId);
  const analysis = useAnalysisStore((s) => s.analysis);
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);

  const renderStore = useRenderStore();

  const { sendMessage, isConnected } = useChatWs();

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  // When analysis completes and we're connected, silently trigger the LLM
  // to produce its opening analysis — no fake user bubble
  useEffect(() => {
    if (analysis && isConnected && !initialAnalysisSent) {
      setInitialAnalysisSent(true);
      sendMessage("Analyze this track and present your initial creative vision.");
    }
  }, [analysis, isConnected, initialAnalysisSent, setInitialAnalysisSent, sendMessage]);

  // When phase transitions to "rendering" and we have a render spec,
  // trigger the actual render and navigate to editor
  useEffect(() => {
    if (phase === "rendering" && renderSpec && !renderTriggered.current) {
      renderTriggered.current = true;

      if (jobId) {
        renderStore.setStatus("rendering");
        renderStore.setProgress(0, "Starting render...");

        fetch("/api/render/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: jobId,
            render_spec: renderSpec,
          }),
        })
          .then((res) => {
            if (!res.ok) throw new Error(`Render failed: ${res.status}`);
            return res.json();
          })
          .then((data) => {
            if (data.render_id) {
              renderStore.setRenderId(data.render_id);
            }
            // Use the download_url directly from render response
            if (data.download_url) {
              renderStore.setDownloadUrl(data.download_url);
            } else if (data.render_id && data.status === "complete") {
              // Fallback: fetch the download URL
              fetch(`/api/render/${data.render_id}/download`)
                .then((r) => r.json())
                .then((d) => {
                  if (d.download_url) {
                    renderStore.setDownloadUrl(d.download_url);
                  }
                });
            }
            // Navigate to editor
            setView("editor");
          })
          .catch((err) => {
            console.error("Render error:", err);
            renderStore.setError(String(err));
            // Still navigate to editor so user sees status
            setView("editor");
          });
      }
    }
  }, [phase, renderSpec, setView, jobId, renderStore]);

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
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-bg-secondary px-6 py-3">
        <h2 className="text-sm font-semibold text-text-primary">Creative Director</h2>
        {analysis && <PhaseIndicator phase={phase} />}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {/* Analysis checklist — always first in chat */}
        {(isAnalyzing || analysis) && (
          <div className="flex gap-3 flex-row">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full mt-0.5 bg-bg-tertiary">
              <Sparkles size={14} className="text-accent" />
            </div>
            <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-bg-tertiary/70 px-4 py-3">
              <AnalysisProgress />
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {renderSpec && phase === "rendering" && (
          <div className="mx-auto max-w-md rounded-xl border border-accent/20 bg-accent/5 p-4 text-center">
            <Clapperboard size={20} className="mx-auto mb-2 text-accent" />
            <p className="text-sm font-medium text-text-primary">Rendering your video...</p>
            <p className="mt-1 text-xs text-text-secondary">
              Template: {(renderSpec as any).global_style?.template ?? (renderSpec as any).globalStyle?.template ?? "—"} | {(renderSpec as any).sections?.length ?? 0} sections
            </p>
            <div className="mt-2">
              <Loader2 size={16} className="mx-auto animate-spin text-accent" />
            </div>
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center gap-2 pl-10 text-xs text-text-secondary">
            <Loader2 size={12} className="animate-spin text-accent" />
            <span>Thinking...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border bg-bg-secondary p-3 px-6">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={getPlaceholder(phase, !!analysis)}
            disabled={!canSend}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-border bg-bg-tertiary px-4 py-2.5 text-sm text-text-primary placeholder:text-text-secondary/40 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 disabled:opacity-40"
            style={{ minHeight: "2.5rem", maxHeight: "8rem" }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "auto";
              target.style.height = Math.min(target.scrollHeight, 128) + "px";
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !canSend}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-white transition hover:bg-accent-hover disabled:opacity-30 disabled:hover:bg-accent"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
