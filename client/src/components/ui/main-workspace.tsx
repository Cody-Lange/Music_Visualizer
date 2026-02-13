import { PreviewPanel } from "@/components/visualizer/preview-panel";
import { ChatPanel } from "@/components/chat/chat-panel";
import { TimelinePanel } from "@/components/timeline/timeline-panel";

export function MainWorkspace() {
  return (
    <div className="flex h-full flex-col">
      {/* Top: Preview + Chat side by side */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 border-r border-border">
          <PreviewPanel />
        </div>
        <div className="w-[420px] min-w-[340px]">
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
