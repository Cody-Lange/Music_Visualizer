import { useAudioStore } from "@/stores/audio-store";
import { Header } from "@/components/ui/header";
import { AudioUploadZone } from "@/components/audio/audio-upload-zone";
import { ChatPage } from "@/components/chat/chat-page";
import { MainWorkspace } from "@/components/ui/main-workspace";
import { ChatWebSocketProvider } from "@/providers/chat-ws-provider";

export default function App() {
  const view = useAudioStore((s) => s.view);

  return (
    <ChatWebSocketProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          {view === "home" && <AudioUploadZone />}
          {view === "chat" && <ChatPage />}
          {view === "editor" && <MainWorkspace />}
        </main>
      </div>
    </ChatWebSocketProvider>
  );
}
