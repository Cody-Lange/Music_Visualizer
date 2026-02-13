import type { LyricsData } from "@/types/lyrics";
import type { LyricsDisplayConfig } from "@/types/render";

interface Props {
  lyrics: LyricsData;
  currentTime: number;
  config: LyricsDisplayConfig;
}

/**
 * Lyrics overlay — displays timed lyrics over the visualization.
 */
export function LyricsOverlay({ lyrics, currentTime, config }: Props) {
  if (!config.enabled || lyrics.lines.length === 0) return null;

  // Find current and next lines
  const currentLineIdx = lyrics.lines.findIndex(
    (line) => currentTime >= line.startTime && currentTime < line.endTime,
  );

  const currentLine = currentLineIdx >= 0 ? lyrics.lines[currentLineIdx] : null;

  if (!currentLine) return null;

  const fontSize = config.size === "small" ? 20 : config.size === "large" ? 36 : 28;
  const fontFamily =
    config.font === "serif"
      ? "Georgia, serif"
      : config.font === "mono"
        ? "JetBrains Mono, monospace"
        : "Inter, sans-serif";

  return (
    <div
      style={{
        position: "absolute",
        bottom: "10%",
        left: "5%",
        right: "5%",
        textAlign: "center",
        pointerEvents: "none",
      }}
    >
      <p
        style={{
          fontSize,
          fontFamily,
          color: config.color,
          textShadow: config.shadow ? "0 2px 8px rgba(0,0,0,0.8)" : "none",
          lineHeight: 1.4,
          margin: 0,
        }}
      >
        {/* Word-by-word highlighting for karaoke mode */}
        {config.animation === "karaoke"
          ? currentLine.words.map((word, i) => {
              const isActive = currentTime >= word.startTime;
              return (
                <span
                  key={i}
                  style={{
                    opacity: isActive ? 1 : 0.4,
                    transition: "opacity 0.1s",
                  }}
                >
                  {word.text}{" "}
                </span>
              );
            })
          : currentLine.text}
      </p>
    </div>
  );
}
