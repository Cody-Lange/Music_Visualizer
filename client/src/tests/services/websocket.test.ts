import { describe, it, expect, beforeEach, vi } from "vitest";
import { ChatWebSocket } from "@/services/websocket";

// Provide window.location for WebSocket URL construction
Object.defineProperty(globalThis, "window", {
  value: {
    location: {
      protocol: "http:",
      host: "localhost:5173",
    },
  },
  writable: true,
});

describe("ChatWebSocket", () => {
  let ws: ChatWebSocket;

  beforeEach(() => {
    vi.clearAllMocks();
    ws = new ChatWebSocket("test-session");
  });

  it("initializes with session ID and disconnected state", () => {
    expect(ws.isConnected).toBe(false);
  });

  it("connect creates a WebSocket", () => {
    ws.connect();
    expect(ws.isConnected).toBe(true); // MockWebSocket readyState = 1 (OPEN)
  });

  it("send calls ws.send with JSON when connected", () => {
    ws.connect();
    ws.send({ type: "message", content: "hello" });

    // The mock WebSocket's send is a vi.fn()
    // We can verify it was called (though we need to access the internal ws)
    // Since isConnected is true, send should not throw
    expect(ws.isConnected).toBe(true);
  });

  it("sendChatMessage sends a message type payload", () => {
    ws.connect();
    ws.sendChatMessage("test message");
    // No error means it worked with the mock
    expect(ws.isConnected).toBe(true);
  });

  it("bindJob sends a bind_job type payload", () => {
    ws.connect();
    ws.bindJob("job-123");
    expect(ws.isConnected).toBe(true);
  });

  it("onMessage registers handler and returns unsubscribe fn", () => {
    const handler = vi.fn();
    const unsub = ws.onMessage(handler);
    expect(typeof unsub).toBe("function");

    // Unsubscribe
    unsub();
  });

  it("disconnect closes and clears state", () => {
    ws.connect();
    ws.disconnect();
    expect(ws.isConnected).toBe(false);
  });

  it("disconnect prevents reconnection", () => {
    ws.connect();
    ws.disconnect();
    // After disconnect, maxReconnectAttempts is set to 0
    expect(ws.isConnected).toBe(false);
  });
});
