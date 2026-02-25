import { describe, it, expect, beforeEach } from "vitest";
import { useVisualizerStore } from "@/stores/visualizer-store";

describe("useVisualizerStore", () => {
  beforeEach(() => {
    useVisualizerStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useVisualizerStore.getState();
    expect(state.customShaderCode).toBeNull();
    expect(state.shaderDescription).toBeNull();
    expect(state.shaderError).toBeNull();
    expect(state.isGeneratingShader).toBe(false);
    expect(state.isPreviewPlaying).toBe(false);
  });

  it("setCustomShaderCode updates shader and clears error", () => {
    useVisualizerStore.getState().setShaderError("some error");
    useVisualizerStore.getState().setCustomShaderCode("void mainImage(out vec4 f, in vec2 c) { f = vec4(1.0); }");

    const state = useVisualizerStore.getState();
    expect(state.customShaderCode).toContain("mainImage");
    expect(state.shaderError).toBeNull();
  });

  it("setShaderDescription stores the description", () => {
    useVisualizerStore.getState().setShaderDescription("Raymarched fractal nebula");
    expect(useVisualizerStore.getState().shaderDescription).toBe("Raymarched fractal nebula");
  });

  it("setIsPreviewPlaying updates playing state", () => {
    useVisualizerStore.getState().setIsPreviewPlaying(true);
    expect(useVisualizerStore.getState().isPreviewPlaying).toBe(true);

    useVisualizerStore.getState().setIsPreviewPlaying(false);
    expect(useVisualizerStore.getState().isPreviewPlaying).toBe(false);
  });

  it("reset restores defaults", () => {
    useVisualizerStore.getState().setCustomShaderCode("some code");
    useVisualizerStore.getState().setShaderDescription("desc");
    useVisualizerStore.getState().setIsPreviewPlaying(true);
    useVisualizerStore.getState().setIsGeneratingShader(true);
    useVisualizerStore.getState().reset();

    const state = useVisualizerStore.getState();
    expect(state.customShaderCode).toBeNull();
    expect(state.shaderDescription).toBeNull();
    expect(state.shaderError).toBeNull();
    expect(state.isGeneratingShader).toBe(false);
    expect(state.isPreviewPlaying).toBe(false);
  });
});
