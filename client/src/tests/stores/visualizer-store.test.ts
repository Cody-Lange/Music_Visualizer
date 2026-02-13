import { describe, it, expect, beforeEach } from "vitest";
import { useVisualizerStore } from "@/stores/visualizer-store";

describe("useVisualizerStore", () => {
  beforeEach(() => {
    useVisualizerStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useVisualizerStore.getState();
    expect(state.activeTemplate).toBe("nebula");
    expect(state.isPreviewPlaying).toBe(false);
  });

  it("setActiveTemplate updates the template", () => {
    useVisualizerStore.getState().setActiveTemplate("geometric");
    expect(useVisualizerStore.getState().activeTemplate).toBe("geometric");
  });

  it("setActiveTemplate to each template type", () => {
    const templates = [
      "nebula", "geometric", "waveform", "cinematic",
      "retro", "nature", "abstract", "urban",
      "glitchbreak", "90s-anime",
    ] as const;

    for (const template of templates) {
      useVisualizerStore.getState().setActiveTemplate(template);
      expect(useVisualizerStore.getState().activeTemplate).toBe(template);
    }
  });

  it("setIsPreviewPlaying updates playing state", () => {
    useVisualizerStore.getState().setIsPreviewPlaying(true);
    expect(useVisualizerStore.getState().isPreviewPlaying).toBe(true);

    useVisualizerStore.getState().setIsPreviewPlaying(false);
    expect(useVisualizerStore.getState().isPreviewPlaying).toBe(false);
  });

  it("reset restores defaults", () => {
    useVisualizerStore.getState().setActiveTemplate("retro");
    useVisualizerStore.getState().setIsPreviewPlaying(true);
    useVisualizerStore.getState().reset();

    const state = useVisualizerStore.getState();
    expect(state.activeTemplate).toBe("nebula");
    expect(state.isPreviewPlaying).toBe(false);
  });
});
