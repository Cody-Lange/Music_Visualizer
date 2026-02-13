import { Canvas } from "@react-three/fiber";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { useAudioFeatures } from "@/hooks/use-audio-features";
import { NebulaScene } from "@/components/visualizer/scenes/nebula-scene";
import { GeometricScene } from "@/components/visualizer/scenes/geometric-scene";
import { WaveformScene } from "@/components/visualizer/scenes/waveform-scene";
import { GlitchbreakScene } from "@/components/visualizer/scenes/glitchbreak-scene";
import { Anime90sScene } from "@/components/visualizer/scenes/anime90s-scene";

const SCENE_BACKGROUNDS: Record<string, string> = {
  glitchbreak: "#050008",
  "90s-anime": "#0D0820",
};

export function VisualizerCanvas() {
  const template = useVisualizerStore((s) => s.activeTemplate);
  const { features, beatState } = useAudioFeatures();

  const bgColor = SCENE_BACKGROUNDS[template] ?? "#0A0A0F";

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 60 }}
      className="!absolute inset-0"
      gl={{ antialias: true, alpha: false }}
    >
      <color attach="background" args={[bgColor]} />
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />

      {template === "nebula" && (
        <NebulaScene features={features} beatState={beatState} />
      )}
      {template === "geometric" && (
        <GeometricScene features={features} beatState={beatState} />
      )}
      {template === "glitchbreak" && (
        <GlitchbreakScene features={features} beatState={beatState} />
      )}
      {template === "90s-anime" && (
        <Anime90sScene features={features} beatState={beatState} />
      )}
      {(template === "waveform" ||
        !["nebula", "geometric", "glitchbreak", "90s-anime"].includes(template)) && (
        <WaveformScene features={features} beatState={beatState} />
      )}
    </Canvas>
  );
}
