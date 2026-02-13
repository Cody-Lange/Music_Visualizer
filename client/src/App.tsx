import { useAudioStore } from "@/stores/audio-store";
import { Header } from "@/components/ui/header";
import { AudioUploadZone } from "@/components/audio/audio-upload-zone";
import { MainWorkspace } from "@/components/ui/main-workspace";

export default function App() {
  const jobId = useAudioStore((s) => s.jobId);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header />
      <main className="flex-1 overflow-hidden">
        {jobId ? <MainWorkspace /> : <AudioUploadZone />}
      </main>
    </div>
  );
}
