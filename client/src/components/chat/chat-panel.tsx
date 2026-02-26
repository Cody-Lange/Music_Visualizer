import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, CheckCircle2, Sparkles, MessageSquare, Clapperboard, Play, Pencil, Clock, Film } from "lucide-react";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";
import { useAnalysisStore } from "@/stores/analysis-store";
import { useRenderStore } from "@/stores/render-store";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { ChatMessage } from "@/components/chat/chat-message";
import { AnalysisProgress } from "@/components/chat/analysis-progress";
import { useChatWs } from "@/providers/chat-ws-provider";
import type { ChatPhase } from "@/services/websocket";
import type { RenderStatus } from "@/types/chat";

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
    label: "Ready",
    icon: CheckCircle2,
    color: "text-success",
  },
  rendering: {
    label: "Generating Video",
    icon: Clapperboard,
    color: "text-warning",
  },
  editing: {
    label: "Review & Refine",
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
      return "Use the buttons above, or type a message...";
    case "rendering":
      return "Rendering in progress...";
    case "editing":
      return "Describe what you'd like to change...";
  }
}

function ActionButtons({ onAction, onRender }: { onAction: (text: string) => void; onRender: () => void }) {
  return (
    <div className="mx-auto flex max-w-md flex-wrap items-center justify-center gap-2 py-2">
      <button
        onClick={onRender}
        className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-hover"
      >
        <Play size={14} />
        Render Video
      </button>
      <button
        onClick={() => onAction("I'd like to make some changes")}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-tertiary px-4 py-2 text-sm font-medium text-text-secondary transition hover:text-text-primary hover:border-text-secondary"
      >
        <Pencil size={14} />
        Keep Editing
      </button>
    </div>
  );
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function RenderProgressCard() {
  const percentage = useRenderStore((s) => s.percentage);
  const message = useRenderStore((s) => s.message);
  const currentFrame = useRenderStore((s) => s.currentFrame);
  const totalFrames = useRenderStore((s) => s.totalFrames);
  const elapsedSeconds = useRenderStore((s) => s.elapsedSeconds);
  const estimatedRemaining = useRenderStore((s) => s.estimatedRemaining);
  const previewUrl = useRenderStore((s) => s.previewUrl);
  const status = useRenderStore((s) => s.status);

  // Cache-bust preview images so the browser loads the latest frame
  const previewSrc = previewUrl ? `${previewUrl}?t=${Math.floor(Date.now() / 2000)}` : null;

  const statusLabel =
    status === "generating_keyframes" || status === "queued"
      ? "Preparing..."
      : status === "encoding"
        ? "Encoding video..."
        : "Rendering";

  return (
    <div
      ref={(el) => { el?.scrollIntoView({ behavior: "smooth", block: "center" }); }}
      className="mx-auto w-full max-w-lg rounded-xl border border-accent/20 bg-accent/5 p-5"
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
          <Clapperboard size={18} className="text-accent" />
        </div>
        <div>
          <p className="text-sm font-semibold text-text-primary">{statusLabel}</p>
          <p className="text-xs text-text-secondary">{message || "Starting render..."}</p>
        </div>
      </div>

      {/* Preview thumbnail */}
      {previewSrc && (
        <div className="mb-3 overflow-hidden rounded-lg border border-border/30">
          <img
            src={previewSrc}
            alt="Render preview"
            className="w-full object-cover"
            style={{ aspectRatio: "16/9" }}
          />
        </div>
      )}

      {/* Progress bar */}
      <div className="mb-3 h-2.5 w-full overflow-hidden rounded-full bg-bg-tertiary">
        {percentage > 0 ? (
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent to-accent-hover transition-all duration-700 ease-out"
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        ) : (
          <div
            className="h-full rounded-full bg-accent/50"
            style={{ width: "100%", animation: "pulse 1.5s ease-in-out infinite" }}
          />
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <div className="flex items-center gap-3">
          {totalFrames > 0 && (
            <span className="flex items-center gap-1">
              <Film size={11} />
              {currentFrame.toLocaleString()}/{totalFrames.toLocaleString()}
            </span>
          )}
          {percentage > 0 && (
            <span className="font-medium text-accent">{percentage}%</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {elapsedSeconds > 0 && (
            <span className="flex items-center gap-1">
              <Clock size={11} />
              {formatTime(elapsedSeconds)}
            </span>
          )}
          {estimatedRemaining != null && estimatedRemaining > 0 && (
            <span className="text-text-secondary/70">
              ~{formatTime(estimatedRemaining)} left
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChatPanel() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const renderTriggered = useRef(false);
  const lastRenderedSpec = useRef<unknown>(null);

  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const addMessage = useChatStore((s) => s.addMessage);
  const phase = useChatStore((s) => s.phase);
  const setPhase = useChatStore((s) => s.setPhase);
  const renderSpec = useChatStore((s) => s.renderSpec);
  const initialAnalysisSent = useChatStore((s) => s.initialAnalysisSent);
  const setInitialAnalysisSent = useChatStore((s) => s.setInitialAnalysisSent);

  const setView = useAudioStore((s) => s.setView);
  const jobId = useAudioStore((s) => s.jobId);
  const analysis = useAnalysisStore((s) => s.analysis);
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);

  const renderError = useRenderStore((s) => s.error);
  const downloadUrl = useRenderStore((s) => s.downloadUrl);
  const resetRender = useRenderStore((s) => s.reset);
  const setRenderStatus = useRenderStore((s) => s.setStatus);
  const setRenderProgress = useRenderStore((s) => s.setProgress);
  const setRenderId = useRenderStore((s) => s.setRenderId);
  const setDownloadUrl = useRenderStore((s) => s.setDownloadUrl);
  const setRenderError = useRenderStore((s) => s.setError);

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
  // submit the render job and start polling for progress.
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollFailures = useRef(0);

  useEffect(() => {
    if (phase !== "rendering" || !renderSpec) return;
    if (!jobId) return;
    // Don't re-render the exact same spec (prevents the server/client
    // phase-desync loop from triggering duplicate renders).
    // Use JSON comparison — object identity (===) fails on re-renders.
    const specKey = JSON.stringify(renderSpec);
    if (lastRenderedSpec.current === specKey) return;

    renderTriggered.current = true;
    lastRenderedSpec.current = specKey;
    pollFailures.current = 0;

    resetRender();
    setRenderStatus("rendering");
    setRenderProgress(0, "Starting render...");

    // Strip useAiKeyframes — it's stored separately on the job
    const { useAiKeyframes: _, ...cleanSpec } = renderSpec as unknown as Record<string, unknown>;

    // Send the preview shader so the server renders the exact same visual
    const previewShaderCode = useVisualizerStore.getState().customShaderCode;

    // Submit render job (returns immediately with render_id)
    fetch("/api/render/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId, renderSpec: cleanSpec, shaderCode: previewShaderCode }),
    })
      .then(async (res) => {
        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const errBody = await res.json();
            detail = errBody.detail || JSON.stringify(errBody);
          } catch { /* ignore parse errors */ }
          throw new Error(detail);
        }
        return res.json();
      })
      .then((data) => {
        if (!data.render_id) throw new Error("No render_id returned");
        setRenderId(data.render_id);

        // Start polling for progress every 1.5 seconds
        const rid = data.render_id;
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
          try {
            const res = await fetch(`/api/render/${rid}/status`);
            if (!res.ok) {
              pollFailures.current++;
              if (pollFailures.current >= 20) {
                // 30s of consecutive failures — give up
                clearInterval(pollRef.current!);
                pollRef.current = null;
                renderTriggered.current = false;
                setRenderError("Lost connection to render server");
                setPhase("confirmation");
              }
              return;
            }
            pollFailures.current = 0;
            const status = await res.json();

            // Update render store with progress
            const pct = status.percentage ?? 0;
            const msg = status.message ?? "";
            setRenderProgress(pct, msg);
            if (status.status && status.status !== "complete" && status.status !== "error") {
              setRenderStatus(status.status as RenderStatus);
            }

            // Update extended progress fields on the store
            useRenderStore.getState().setProgressDetails?.({
              currentFrame: status.current_frame,
              totalFrames: status.total_frames,
              elapsedSeconds: status.elapsed_seconds,
              estimatedRemaining: status.estimated_remaining,
              previewUrl: status.preview_url,
            });

            // Terminal states: stop polling
            if (status.status === "complete") {
              clearInterval(pollRef.current!);
              pollRef.current = null;
              if (status.download_url) {
                setDownloadUrl(status.download_url);
              }
              setRenderStatus("complete");
              setRenderProgress(100, "Complete!");
              renderTriggered.current = false;
              setPhase("editing");
              setView("editor");
            } else if (status.status === "error") {
              clearInterval(pollRef.current!);
              pollRef.current = null;
              setRenderError(status.error || "Render failed");
              renderTriggered.current = false;
              setPhase("confirmation");
              addMessage({
                id: createMessageId(),
                role: "system",
                content: `Render failed: ${status.error || "Unknown error"}. You can try again using the buttons below.`,
                timestamp: Date.now(),
              });
            }
          } catch (e) {
            console.warn("Render poll error:", e);
            pollFailures.current++;
            if (pollFailures.current >= 20) {
              clearInterval(pollRef.current!);
              pollRef.current = null;
              renderTriggered.current = false;
              setRenderError("Lost connection to render server");
              setPhase("confirmation");
            }
          }
        }, 1500);
      })
      .catch((err) => {
        console.error("Render error:", err);
        setRenderError(String(err));
        renderTriggered.current = false;
        setPhase("confirmation");
        addMessage({
          id: createMessageId(),
          role: "system",
          content: `Render failed: ${err.message ?? err}. You can try again using the buttons below.`,
          timestamp: Date.now(),
        });
      });

    // Cleanup: stop polling when unmounting or phase changes.
    // Also reset renderTriggered so re-renders aren't blocked.
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      renderTriggered.current = false;
    };
  }, [phase, renderSpec, jobId, setView, setPhase, addMessage, resetRender, setRenderStatus, setRenderProgress, setRenderId, setDownloadUrl, setRenderError]);

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

  const handleActionButton = useCallback((text: string) => {
    if (isStreaming) return;

    addMessage({
      id: createMessageId(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    });

    sendMessage(text);
  }, [isStreaming, addMessage, sendMessage]);

  const handleRenderButton = useCallback(() => {
    if (isStreaming) return;

    addMessage({
      id: createMessageId(),
      role: "user",
      content: "Render it",
      timestamp: Date.now(),
    });

    // Send with render_confirm flag so the server knows this is an
    // explicit button press, not casual conversation text
    sendMessage("Render it", true);
  }, [isStreaming, addMessage, sendMessage]);

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

        {/* Action buttons in confirmation and editing phases */}
        {(phase === "confirmation" || phase === "editing") && !isStreaming && (
          <ActionButtons onAction={handleActionButton} onRender={handleRenderButton} />
        )}

        {renderSpec && phase === "rendering" && !renderError && !downloadUrl && (
          <RenderProgressCard />
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
