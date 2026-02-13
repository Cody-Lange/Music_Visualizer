import type { SectionSpec } from "@/types/render";

interface Props {
  section: SectionSpec | null;
  transitionProgress: number;
}

/**
 * Background layer — renders section-based colored backgrounds.
 * In Tier 2, this would display AI keyframe images.
 */
export function BackgroundLayer({ section, transitionProgress }: Props) {
  const colors = section?.colorPalette ?? ["#0A0A0F", "#1A1A28"];
  const primary = colors[0] ?? "#0A0A0F";
  const secondary = colors[1] ?? "#1A1A28";

  // Gradient opacity transitions between sections
  const opacity = Math.min(1, transitionProgress * 2);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: `linear-gradient(135deg, ${primary}, ${secondary})`,
        opacity,
      }}
    />
  );
}
