import { describe, it, expect, beforeEach } from "vitest";
import { useRenderStore } from "@/stores/render-store";

describe("useRenderStore", () => {
  beforeEach(() => {
    useRenderStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useRenderStore.getState();
    expect(state.renderId).toBeNull();
    expect(state.status).toBe("idle");
    expect(state.percentage).toBe(0);
    expect(state.message).toBe("");
    expect(state.downloadUrl).toBeNull();
    expect(state.error).toBeNull();
  });

  it("setRenderId updates render ID", () => {
    useRenderStore.getState().setRenderId("render-123");
    expect(useRenderStore.getState().renderId).toBe("render-123");
  });

  it("setStatus updates status", () => {
    useRenderStore.getState().setStatus("rendering");
    expect(useRenderStore.getState().status).toBe("rendering");
  });

  it("setProgress updates percentage and message", () => {
    useRenderStore.getState().setProgress(75, "Encoding frames...");

    const state = useRenderStore.getState();
    expect(state.percentage).toBe(75);
    expect(state.message).toBe("Encoding frames...");
  });

  it("setDownloadUrl also sets status to complete and percentage to 100", () => {
    useRenderStore.getState().setDownloadUrl("/storage/renders/video.mp4");

    const state = useRenderStore.getState();
    expect(state.downloadUrl).toBe("/storage/renders/video.mp4");
    expect(state.status).toBe("complete");
    expect(state.percentage).toBe(100);
  });

  it("setError sets error and status to error", () => {
    useRenderStore.getState().setError("FFmpeg crashed");

    const state = useRenderStore.getState();
    expect(state.error).toBe("FFmpeg crashed");
    expect(state.status).toBe("error");
  });

  it("reset clears all state", () => {
    useRenderStore.getState().setRenderId("r1");
    useRenderStore.getState().setDownloadUrl("/video.mp4");
    useRenderStore.getState().reset();

    const state = useRenderStore.getState();
    expect(state.renderId).toBeNull();
    expect(state.status).toBe("idle");
    expect(state.percentage).toBe(0);
    expect(state.downloadUrl).toBeNull();
    expect(state.error).toBeNull();
  });
});
