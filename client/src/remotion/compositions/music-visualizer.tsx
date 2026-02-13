/**
 * Main Remotion composition for the Music Visualizer.
 *
 * This defines the frame-by-frame rendering logic used by
 * Remotion to produce the final MP4 video. Each frame is
 * rendered deterministically from the audio analysis data.
 *
 * Note: This composition is designed to be rendered by Remotion's
 * CLI on the server. In the browser preview, we use the real-time
 * Three.js visualizer instead.
 */

import type { AudioAnalysis } from "@/types/audio";
import type { LyricsData } from "@/types/lyrics";
import type { RenderSpec } from "@/types/render";
import {
  getCurrentSection,
  getBeatStateAtTime,
  getAudioFeaturesAtTime,
} from "@/remotion/utils/audio-helpers";
import { BackgroundLayer } from "@/remotion/components/background-layer";
import { LyricsOverlay } from "@/remotion/components/lyrics-overlay";
import { BeatEffectsLayer } from "@/remotion/components/beat-effects-layer";

interface Props {
  renderSpec: RenderSpec;
  audioAnalysis: AudioAnalysis;
  lyrics: LyricsData | null;
  fps: number;
  frame: number;
}

/**
 * Pure function: given a frame number, produce the visual state.
 * This is the core of the Remotion composition.
 */
export function MusicVisualizerFrame({
  renderSpec,
  audioAnalysis,
  lyrics,
  fps,
  frame,
}: Props) {
  const currentTime = frame / fps;

  // Get current section
  const currentSection = getCurrentSection(renderSpec.sections, currentTime);

  // Get beat state
  const beatState = getBeatStateAtTime(audioAnalysis.rhythm.beats, currentTime);

  // Get audio features at this exact time
  const audioFeatures = getAudioFeaturesAtTime(audioAnalysis, currentTime);

  // Detect section transitions (within 0.5s of a boundary)
  const isSectionTransition = renderSpec.sections.some(
    (s) => Math.abs(currentTime - s.startTime) < 0.25 && s.startTime > 0,
  );

  // Compute transition progress (0-1, how far into the current section)
  const sectionStart = currentSection?.startTime ?? 0;
  const sectionEnd = currentSection?.endTime ?? audioAnalysis.metadata.duration;
  const sectionDuration = sectionEnd - sectionStart;
  const transitionProgress =
    sectionDuration > 0 ? (currentTime - sectionStart) / sectionDuration : 1;

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        backgroundColor: "#0A0A0F",
      }}
    >
      {/* Layer 0: Background */}
      <BackgroundLayer
        section={currentSection}
        transitionProgress={transitionProgress}
      />

      {/* Layer 1-3: Procedural visuals would be rendered here
          In the actual Remotion render, we'd use @remotion/three
          to render the same Three.js scenes from the preview */}

      {/* Layer 4: Lyrics */}
      {lyrics && (
        <LyricsOverlay
          lyrics={lyrics}
          currentTime={currentTime}
          config={renderSpec.globalStyle.lyricsDisplay}
        />
      )}

      {/* Layer 5: Beat effects */}
      <BeatEffectsLayer
        beatIntensity={beatState.intensity}
        rms={audioFeatures.rms}
        isSectionTransition={isSectionTransition}
      />
    </div>
  );
}
