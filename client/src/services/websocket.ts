/**
 * WebSocket client for chat streaming and progress updates.
 */

export type WsMessageType =
  | "bind_job"
  | "message"
  | "stream_start"
  | "stream_chunk"
  | "stream_end"
  | "system"
  | "error"
  | "phase"
  | "render_spec";

export type ChatPhase = "analysis" | "refinement" | "confirmation" | "rendering" | "editing";

export interface WsMessage {
  type: WsMessageType;
  content?: string;
  job_id?: string;
  phase?: ChatPhase;
  render_spec?: Record<string, unknown>;
  render_confirm?: boolean;
}

type MessageHandler = (message: WsMessage) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private sessionId: string;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/chat/${this.sessionId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WsMessage;
        this.handlers.forEach((handler) => handler(message));
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onerror = () => {
      // Error handling is done in onclose
    };
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  send(message: WsMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  sendChatMessage(content: string, renderConfirm?: boolean): void {
    this.send({ type: "message", content, ...(renderConfirm ? { render_confirm: true } : {}) });
  }

  bindJob(jobId: string): void {
    this.send({ type: "bind_job", job_id: jobId });
  }

  disconnect(): void {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
    this.ws = null;
    this.handlers = [];
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
