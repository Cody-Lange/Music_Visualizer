import { useState, useCallback, useRef } from "react";
import { GripVertical } from "lucide-react";
import { PreviewPanel } from "@/components/visualizer/preview-panel";
import { ChatPanel } from "@/components/chat/chat-panel";
import { TimelinePanel } from "@/components/timeline/timeline-panel";

const MIN_CHAT_WIDTH = 320;
const MAX_CHAT_WIDTH = 800;
const DEFAULT_CHAT_WIDTH = 420;

export function MainWorkspace() {
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const newWidth = containerRect.right - ev.clientX;
      setChatWidth(Math.max(MIN_CHAT_WIDTH, Math.min(MAX_CHAT_WIDTH, newWidth)));
    };

    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Top: Preview + Resizable Chat side by side */}
      <div ref={containerRef} className="flex flex-1 min-h-0">
        <div className="flex-1 border-r border-border">
          <PreviewPanel />
        </div>

        {/* Drag handle */}
        <div
          onMouseDown={handleMouseDown}
          className="group flex w-2 cursor-col-resize items-center justify-center bg-bg-secondary hover:bg-accent/20 transition-colors"
          title="Drag to resize chat panel"
        >
          <GripVertical size={12} className="text-text-secondary/40 group-hover:text-accent" />
        </div>

        {/* Chat panel with dynamic width */}
        <div style={{ width: chatWidth, minWidth: MIN_CHAT_WIDTH, maxWidth: MAX_CHAT_WIDTH }}>
          <ChatPanel />
        </div>
      </div>

      {/* Bottom: Timeline */}
      <div className="h-48 border-t border-border">
        <TimelinePanel />
      </div>
    </div>
  );
}
