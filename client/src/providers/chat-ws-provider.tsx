import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from "react";
import { ChatWebSocket } from "@/services/websocket";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";
import { useVisualizerStore } from "@/stores/visualizer-store";

interface ChatWsContextType {
  sendMessage: (content: string) => void;
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

            // Auto-generate shader from the render spec's shader description
            const globalStyle = (message.render_spec as any)?.globalStyle;
            const shaderDesc = globalStyle?.shaderDescription;
            if (shaderDesc && typeof shaderDesc === "string") {
              autoGenerateShader(shaderDesc);
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

  const sendMessage = useCallback((content: string) => {
    wsRef.current?.sendChatMessage(content);
  }, []);

  return (
    <ChatWsContext.Provider value={{ sendMessage, isConnected }}>
      {children}
    </ChatWsContext.Provider>
  );
}
