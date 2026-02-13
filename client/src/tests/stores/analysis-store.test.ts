import { describe, it, expect, beforeEach } from "vitest";
import { useAnalysisStore } from "@/stores/analysis-store";
import type { AudioAnalysis } from "@/types/audio";
import type { LyricsData } from "@/types/lyrics";

describe("useAnalysisStore", () => {
  beforeEach(() => {
    useAnalysisStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useAnalysisStore.getState();
    expect(state.analysis).toBeNull();
    expect(state.lyrics).toBeNull();
    expect(state.analysisStep).toBe("uploading");
    expect(state.analysisProgress).toBe(0);
    expect(state.analysisMessage).toBe("");
    expect(state.isAnalyzing).toBe(false);
  });

  it("setAnalysis updates analysis data", () => {
    const analysis = { metadata: { filename: "test.mp3" } } as unknown as AudioAnalysis;
    useAnalysisStore.getState().setAnalysis(analysis);
    expect(useAnalysisStore.getState().analysis).toBe(analysis);
  });

  it("setLyrics updates lyrics data", () => {
    const lyrics = { source: "genius", lines: [] } as unknown as LyricsData;
    useAnalysisStore.getState().setLyrics(lyrics);
    expect(useAnalysisStore.getState().lyrics).toBe(lyrics);
  });

  it("setProgress updates step, progress, and message", () => {
    useAnalysisStore.getState().setProgress("analyzing", 50, "Extracting features...");

    const state = useAnalysisStore.getState();
    expect(state.analysisStep).toBe("analyzing");
    expect(state.analysisProgress).toBe(50);
    expect(state.analysisMessage).toBe("Extracting features...");
  });

  it("setIsAnalyzing updates analyzing flag", () => {
    useAnalysisStore.getState().setIsAnalyzing(true);
    expect(useAnalysisStore.getState().isAnalyzing).toBe(true);
  });

  it("reset clears all state to defaults", () => {
    useAnalysisStore.getState().setIsAnalyzing(true);
    useAnalysisStore.getState().setProgress("analyzing", 75, "Almost done");

    useAnalysisStore.getState().reset();

    const state = useAnalysisStore.getState();
    expect(state.analysis).toBeNull();
    expect(state.lyrics).toBeNull();
    expect(state.analysisStep).toBe("uploading");
    expect(state.analysisProgress).toBe(0);
    expect(state.isAnalyzing).toBe(false);
  });
});
