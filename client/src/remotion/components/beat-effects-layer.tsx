interface Props {
  beatIntensity: number;
  rms: number;
  isSectionTransition: boolean;
}

/**
 * Beat effects overlay — flash on beat, screen effects on transitions.
 */
export function BeatEffectsLayer({ beatIntensity, rms, isSectionTransition }: Props) {
  return (
    <>
      {/* Beat flash */}
      {beatIntensity > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "white",
            opacity: beatIntensity * 0.15,
            pointerEvents: "none",
          }}
        />
      )}

      {/* Vignette — intensity based on RMS */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at center, transparent ${50 + rms * 20}%, rgba(0,0,0,${0.5 - rms * 0.2}) 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* Section transition flash */}
      {isSectionTransition && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "white",
            opacity: 0.3,
            pointerEvents: "none",
          }}
        />
      )}
    </>
  );
}
