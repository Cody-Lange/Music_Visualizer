// Vitest setup file — global mocks for browser APIs

import { vi } from "vitest";

// Mock AudioContext
class MockAnalyserNode {
  fftSize = 2048;
  smoothingTimeConstant = 0.8;
  frequencyBinCount = 1024;
  connect = vi.fn();
  getByteFrequencyData = vi.fn((arr: Uint8Array) => arr.fill(128));
  getByteTimeDomainData = vi.fn((arr: Uint8Array) => arr.fill(128));
}

class MockAudioContext {
  destination = {};
  createAnalyser = vi.fn(() => new MockAnalyserNode());
  createMediaElementSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }));
  decodeAudioData = vi.fn();
}

Object.defineProperty(globalThis, "AudioContext", {
  value: MockAudioContext,
  writable: true,
});

// Mock URL.createObjectURL / revokeObjectURL
Object.defineProperty(globalThis.URL, "createObjectURL", {
  value: vi.fn(() => "blob:mock-url"),
  writable: true,
});
Object.defineProperty(globalThis.URL, "revokeObjectURL", {
  value: vi.fn(),
  writable: true,
});

// Mock requestAnimationFrame
globalThis.requestAnimationFrame = vi.fn((cb) => {
  return setTimeout(cb, 0) as unknown as number;
});
globalThis.cancelAnimationFrame = vi.fn((id) => clearTimeout(id));

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn();
}

Object.defineProperty(globalThis, "WebSocket", {
  value: MockWebSocket,
  writable: true,
});
