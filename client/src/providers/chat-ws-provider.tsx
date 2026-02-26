import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from "react";
import { ChatWebSocket } from "@/services/websocket";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";
import { useVisualizerStore } from "@/stores/visualizer-store";

interface ChatWsContextType {
  sendMessage: (content: string, renderConfirm?: boolean) => void;
  isConnected: boolean;
}

const ChatWsContext = createContext<ChatWsContextType>({
  sendMessage: () => {},
  isConnected: false,
});

export function useChatWs() {
  return useContext(ChatWsContext);
}

/**
 * Auto-generate a GLSL shader from a description via the /api/shader/generate endpoint.
 * Runs in the background — updates the visualizer store on success.
 */
async function autoGenerateShader(description: string, moodTags: string[] = []) {
  const vizStore = useVisualizerStore.getState();
  vizStore.setIsGeneratingShader(true);
  vizStore.setShaderError(null);

  try {
    const res = await fetch("/api/shader/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description, mood_tags: moodTags }),
    });

    if (!res.ok) return;

    const data = await res.json();
    if (data.shader_code) {
      useVisualizerStore.getState().setCustomShaderCode(data.shader_code);
      useVisualizerStore.getState().setShaderDescription(description);
    }
  } catch (err) {
    console.warn("Auto shader generation failed:", err);
  } finally {
    useVisualizerStore.getState().setIsGeneratingShader(false);
  }
}

export function ChatWebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<ChatWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const sessionId = useChatStore((s) => s.sessionId);
  const jobId = useAudioStore((s) => s.jobId);

  useEffect(() => {
    if (!jobId) return;

    const ws = new ChatWebSocket(sessionId);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((message) => {
      const store = useChatStore.getState();

      switch (message.type) {
        case "stream_start":
          store.setIsStreaming(true);
          store.addMessage({
            id: createMessageId(),
            role: "assistant",
            content: "",
            timestamp: Date.now(),
            isStreaming: true,
          });
          break;

        case "stream_chunk":
          if (message.content) {
            const s = useChatStore.getState();
            const lastMsg = s.messages[s.messages.length - 1];
            s.updateLastAssistantMessage((lastMsg?.content ?? "") + message.content);
          }
          break;

        case "stream_end":
          useChatStore.getState().setIsStreaming(false);
          break;

        case "system":
          if (message.content?.includes("bound to job")) {
            setIsConnected(true);
          }
          if (message.content && !message.content.includes("bound to job")) {
            useChatStore.getState().addMessage({
              id: createMessageId(),
              role: "system",
              content: message.content,
              timestamp: Date.now(),
            });
          }
          break;

        case "phase":
          if (message.phase) {
            useChatStore.getState().setPhase(message.phase);
          }
          break;

        case "render_spec":
          if (message.render_spec) {
            useChatStore.getState().setRenderSpec(message.render_spec as any);

            // Only auto-generate a shader when the user is still
            // previewing (refinement / confirmation) AND doesn't already
            // have one.  During "rendering" phase the user has already
            // approved what they see in the preview — re-generating
            // would produce a different shader (LLM non-determinism)
            // AND race with the render submission, causing the rendered
            // video to use the old shader while the preview updates to
            // the new one.  In "editing" phase the user should
            // explicitly ask for changes before we regenerate.
            const currentPhase = useChatStore.getState().phase;
            const hasShader = !!useVisualizerStore.getState().customShaderCode;
            if (currentPhase !== "editing" && currentPhase !== "rendering" && !hasShader) {
              const globalStyle = (message.render_spec as any)?.globalStyle;
              const shaderDesc = globalStyle?.shaderDescription;
              if (shaderDesc && typeof shaderDesc === "string") {
                autoGenerateShader(shaderDesc);
              }
            }
          }
          break;
      }
    });

    ws.connect();

    const bindTimer = setTimeout(() => {
      ws.bindJob(jobId);
      setIsConnected(true);
    }, 500);

    return () => {
      clearTimeout(bindTimer);
      unsubscribe();
      ws.disconnect();
      setIsConnected(false);
    };
  }, [sessionId, jobId]);

  const sendMessage = useCallback((content: string, renderConfirm?: boolean) => {
    wsRef.current?.sendChatMessage(content, renderConfirm);
  }, []);

  return (
    <ChatWsContext.Provider value={{ sendMessage, isConnected }}>
      {children}
    </ChatWsContext.Provider>
  );
}
