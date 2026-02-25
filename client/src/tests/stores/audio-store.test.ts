import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAudioStore } from "@/stores/audio-store";

describe("useAudioStore", () => {
  beforeEach(() => {
    useAudioStore.getState().reset();
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = useAudioStore.getState();
    expect(state.file).toBeNull();
    expect(state.jobId).toBeNull();
    expect(state.audioUrl).toBeNull();
    expect(state.audioBuffer).toBeNull();
    expect(state.view).toBe("home");
    expect(state.isPlaying).toBe(false);
    expect(state.currentTime).toBe(0);
    expect(state.duration).toBe(0);
    expect(state.volume).toBe(0.8);
  });

  it("setFile creates object URL and updates state", () => {
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    useAudioStore.getState().setFile(file, "job-1");

    const state = useAudioStore.getState();
    expect(state.file).toBe(file);
    expect(state.jobId).toBe("job-1");
    expect(state.audioUrl).toBe("blob:mock-url");
    expect(state.currentTime).toBe(0);
    expect(state.isPlaying).toBe(false);
  });

  it("setFile revokes previous URL", () => {
    const file1 = new File(["a"], "a.mp3", { type: "audio/mpeg" });
    const file2 = new File(["b"], "b.mp3", { type: "audio/mpeg" });

    useAudioStore.getState().setFile(file1, "j1");
    useAudioStore.getState().setFile(file2, "j2");

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("setAudioBuffer sets buffer and duration", () => {
    const buffer = { duration: 180.5 } as AudioBuffer;
    useAudioStore.getState().setAudioBuffer(buffer);

    const state = useAudioStore.getState();
    expect(state.audioBuffer).toBe(buffer);
    expect(state.duration).toBe(180.5);
  });

  it("setVolume clamps to 0-1 range", () => {
    useAudioStore.getState().setVolume(1.5);
    expect(useAudioStore.getState().volume).toBe(1);

    useAudioStore.getState().setVolume(-0.3);
    expect(useAudioStore.getState().volume).toBe(0);

    useAudioStore.getState().setVolume(0.65);
    expect(useAudioStore.getState().volume).toBe(0.65);
  });

  it("setIsPlaying updates playing state", () => {
    useAudioStore.getState().setIsPlaying(true);
    expect(useAudioStore.getState().isPlaying).toBe(true);

    useAudioStore.getState().setIsPlaying(false);
    expect(useAudioStore.getState().isPlaying).toBe(false);
  });

  it("setCurrentTime updates current time", () => {
    useAudioStore.getState().setCurrentTime(42.3);
    expect(useAudioStore.getState().currentTime).toBe(42.3);
  });

  it("setView updates the view", () => {
    useAudioStore.getState().setView("chat");
    expect(useAudioStore.getState().view).toBe("chat");

    useAudioStore.getState().setView("editor");
    expect(useAudioStore.getState().view).toBe("editor");

    useAudioStore.getState().setView("home");
    expect(useAudioStore.getState().view).toBe("home");
  });

  it("reset clears all state and revokes URL", () => {
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    useAudioStore.getState().setFile(file, "job-1");
    useAudioStore.getState().setIsPlaying(true);
    useAudioStore.getState().setCurrentTime(30);
    useAudioStore.getState().setView("editor");

    useAudioStore.getState().reset();

    const state = useAudioStore.getState();
    expect(state.file).toBeNull();
    expect(state.jobId).toBeNull();
    expect(state.audioUrl).toBeNull();
    expect(state.view).toBe("home");
    expect(state.isPlaying).toBe(false);
    expect(state.currentTime).toBe(0);
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });
});
