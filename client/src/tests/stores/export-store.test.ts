import { describe, it, expect, beforeEach } from "vitest";
import { useExportStore } from "@/stores/export-store";

describe("useExportStore", () => {
  beforeEach(() => {
    useExportStore.getState().reset();
  });

  it("has correct initial state (youtube preset)", () => {
    const state = useExportStore.getState();
    expect(state.activePreset).toBe("youtube");
    expect(state.settings.resolution).toEqual([1920, 1080]);
    expect(state.settings.fps).toBe(30);
    expect(state.settings.aspectRatio).toBe("16:9");
    expect(state.settings.format).toBe("mp4");
    expect(state.settings.quality).toBe("high");
  });

  it("setPreset switches to tiktok config", () => {
    useExportStore.getState().setPreset("tiktok");

    const state = useExportStore.getState();
    expect(state.activePreset).toBe("tiktok");
    expect(state.settings.resolution).toEqual([1080, 1920]);
    expect(state.settings.aspectRatio).toBe("9:16");
    expect(state.settings.fps).toBe(30);
  });

  it("setPreset switches to instagram config", () => {
    useExportStore.getState().setPreset("instagram");

    const state = useExportStore.getState();
    expect(state.activePreset).toBe("instagram");
    expect(state.settings.resolution).toEqual([1080, 1080]);
    expect(state.settings.aspectRatio).toBe("1:1");
  });

  it("setPreset to 4k sets high resolution", () => {
    useExportStore.getState().setPreset("4k");

    const state = useExportStore.getState();
    expect(state.activePreset).toBe("4k");
    expect(state.settings.resolution).toEqual([3840, 2160]);
  });

  it("setPreset to youtube-hd sets 60fps", () => {
    useExportStore.getState().setPreset("youtube-hd");
    expect(useExportStore.getState().settings.fps).toBe(60);
  });

  it("setResolution switches activePreset to custom", () => {
    useExportStore.getState().setResolution([800, 600]);

    const state = useExportStore.getState();
    expect(state.activePreset).toBe("custom");
    expect(state.settings.resolution).toEqual([800, 600]);
  });

  it("setFps updates fps without changing preset", () => {
    useExportStore.getState().setFps(60);
    expect(useExportStore.getState().settings.fps).toBe(60);
    expect(useExportStore.getState().activePreset).toBe("youtube");
  });

  it("setAspectRatio updates aspect ratio", () => {
    useExportStore.getState().setAspectRatio("1:1");
    expect(useExportStore.getState().settings.aspectRatio).toBe("1:1");
  });

  it("reset restores youtube defaults", () => {
    useExportStore.getState().setPreset("4k");
    useExportStore.getState().reset();

    const state = useExportStore.getState();
    expect(state.activePreset).toBe("youtube");
    expect(state.settings.resolution).toEqual([1920, 1080]);
    expect(state.settings.fps).toBe(30);
  });
});
