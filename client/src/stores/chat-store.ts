import { create } from "zustand";
import type { ChatMessage } from "@/types/chat";
import type { RenderSpec } from "@/types/render";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  renderSpec: RenderSpec | null;
  sessionId: string;

  addMessage: (message: ChatMessage) => void;
  updateLastAssistantMessage: (content: string) => void;
  setIsStreaming: (streaming: boolean) => void;
  setRenderSpec: (spec: RenderSpec) => void;
  reset: () => void;
}

let messageCounter = 0;

export function createMessageId(): string {
  return `msg_${Date.now()}_${++messageCounter}`;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  renderSpec: null,
  sessionId: `session_${Date.now()}`,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastAssistantMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      const lastIdx = messages.length - 1;
      if (lastIdx >= 0 && messages[lastIdx]?.role === "assistant") {
        messages[lastIdx] = { ...messages[lastIdx]!, content, isStreaming: true };
      }
      return { messages };
    }),

  setIsStreaming: (isStreaming) =>
    set((state) => {
      // When streaming ends, mark the last message as not streaming
      if (!isStreaming) {
        const messages = [...state.messages];
        const lastIdx = messages.length - 1;
        if (lastIdx >= 0 && messages[lastIdx]?.role === "assistant") {
          messages[lastIdx] = { ...messages[lastIdx]!, isStreaming: false };
        }
        return { isStreaming, messages };
      }
      return { isStreaming };
    }),

  setRenderSpec: (renderSpec) => set({ renderSpec }),

  reset: () =>
    set({
      messages: [],
      isStreaming: false,
      renderSpec: null,
      sessionId: `session_${Date.now()}`,
    }),
}));
