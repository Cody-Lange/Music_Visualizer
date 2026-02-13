import { useEffect, useRef, useCallback, useState } from "react";
import { ChatWebSocket } from "@/services/websocket";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import { useAudioStore } from "@/stores/audio-store";

export function useChatWebSocket() {
  const wsRef = useRef<ChatWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const sessionId = useChatStore((s) => s.sessionId);
  const addMessage = useChatStore((s) => s.addMessage);
  const updateLastAssistantMessage = useChatStore((s) => s.updateLastAssistantMessage);
  const setIsStreaming = useChatStore((s) => s.setIsStreaming);
  const jobId = useAudioStore((s) => s.jobId);

  useEffect(() => {
    const ws = new ChatWebSocket(sessionId);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((message) => {
      switch (message.type) {
        case "stream_start":
          setIsStreaming(true);
          addMessage({
            id: createMessageId(),
            role: "assistant",
            content: "",
            timestamp: Date.now(),
            isStreaming: true,
          });
          break;

        case "stream_chunk":
          if (message.content) {
            updateLastAssistantMessage(
              (useChatStore.getState().messages.at(-1)?.content ?? "") + message.content,
            );
          }
          break;

        case "stream_end":
          setIsStreaming(false);
          break;

        case "system":
          if (message.content?.includes("bound to job")) {
            setIsConnected(true);
          }
          break;
      }
    });

    ws.connect();

    // Small delay to allow connection to establish, then bind job
    const bindTimer = setTimeout(() => {
      if (jobId) {
        ws.bindJob(jobId);
        setIsConnected(true);
      }
    }, 500);

    return () => {
      clearTimeout(bindTimer);
      unsubscribe();
      ws.disconnect();
    };
  }, [sessionId, jobId, addMessage, updateLastAssistantMessage, setIsStreaming]);

  const sendMessage = useCallback((content: string) => {
    wsRef.current?.sendChatMessage(content);
  }, []);

  return { sendMessage, isConnected };
}
