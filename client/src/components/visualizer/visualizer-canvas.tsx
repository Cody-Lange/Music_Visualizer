import { Canvas } from "@react-three/fiber";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { useAudioFeatures } from "@/hooks/use-audio-features";
import { NebulaScene } from "@/components/visualizer/scenes/nebula-scene";
import { GeometricScene } from "@/components/visualizer/scenes/geometric-scene";
import { WaveformScene } from "@/components/visualizer/scenes/waveform-scene";

export function VisualizerCanvas() {
  const template = useVisualizerStore((s) => s.activeTemplate);
  const { features, beatState } = useAudioFeatures();

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 60 }}
      className="!absolute inset-0"
      gl={{ antialias: true, alpha: false }}
    >
      <color attach="background" args={["#0A0A0F"]} />
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />

      {template === "nebula" && (
        <NebulaScene features={features} beatState={beatState} />
      )}
      {template === "geometric" && (
        <GeometricScene features={features} beatState={beatState} />
      )}
      {(template === "waveform" || !["nebula", "geometric"].includes(template)) && (
        <WaveformScene features={features} beatState={beatState} />
      )}
    </Canvas>
  );
}
