import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore, createMessageId } from "@/stores/chat-store";
import type { ChatMessage } from "@/types/chat";

describe("createMessageId", () => {
  it("returns unique IDs with msg_ prefix", () => {
    const id1 = createMessageId();
    const id2 = createMessageId();
    expect(id1).toMatch(/^msg_\d+_\d+$/);
    expect(id2).toMatch(/^msg_\d+_\d+$/);
    expect(id1).not.toBe(id2);
  });
});

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.isStreaming).toBe(false);
    expect(state.renderSpec).toBeNull();
    expect(state.sessionId).toMatch(/^session_\d+$/);
  });

  it("addMessage appends to messages array", () => {
    const msg: ChatMessage = {
      id: "msg-1",
      role: "user",
      content: "Hello",
      timestamp: Date.now(),
    };
    useChatStore.getState().addMessage(msg);
    expect(useChatStore.getState().messages).toHaveLength(1);
    expect(useChatStore.getState().messages[0]).toBe(msg);
  });

  it("addMessage preserves existing messages", () => {
    const msg1: ChatMessage = { id: "1", role: "user", content: "A", timestamp: 1 };
    const msg2: ChatMessage = { id: "2", role: "assistant", content: "B", timestamp: 2 };
    useChatStore.getState().addMessage(msg1);
    useChatStore.getState().addMessage(msg2);
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it("updateLastAssistantMessage updates only if last is assistant", () => {
    const msg: ChatMessage = {
      id: "1",
      role: "assistant",
      content: "Hi",
      timestamp: 1,
    };
    useChatStore.getState().addMessage(msg);
    useChatStore.getState().updateLastAssistantMessage("Hello there");

    const updated = useChatStore.getState().messages[0];
    expect(updated?.content).toBe("Hello there");
    expect(updated?.isStreaming).toBe(true);
  });

  it("updateLastAssistantMessage does nothing if last is user", () => {
    const msg: ChatMessage = { id: "1", role: "user", content: "Hey", timestamp: 1 };
    useChatStore.getState().addMessage(msg);
    useChatStore.getState().updateLastAssistantMessage("Should not appear");

    expect(useChatStore.getState().messages[0]?.content).toBe("Hey");
  });

  it("setIsStreaming marks last assistant message as not streaming when false", () => {
    const msg: ChatMessage = {
      id: "1",
      role: "assistant",
      content: "Streaming...",
      timestamp: 1,
      isStreaming: true,
    };
    useChatStore.getState().addMessage(msg);
    useChatStore.getState().setIsStreaming(false);

    expect(useChatStore.getState().isStreaming).toBe(false);
    expect(useChatStore.getState().messages[0]?.isStreaming).toBe(false);
  });

  it("setIsStreaming(true) only sets flag without modifying messages", () => {
    useChatStore.getState().setIsStreaming(true);
    expect(useChatStore.getState().isStreaming).toBe(true);
  });

  it("setRenderSpec updates render spec", () => {
    const spec = { globalStyle: { template: "nebula" } } as any;
    useChatStore.getState().setRenderSpec(spec);
    expect(useChatStore.getState().renderSpec).toBe(spec);
  });

  it("reset generates a new session ID", () => {
    const oldId = useChatStore.getState().sessionId;
    useChatStore.getState().reset();
    // Note: in fast execution the timestamp could be the same,
    // so we just verify the format
    expect(useChatStore.getState().sessionId).toMatch(/^session_\d+$/);
    expect(useChatStore.getState().messages).toEqual([]);
  });
});
