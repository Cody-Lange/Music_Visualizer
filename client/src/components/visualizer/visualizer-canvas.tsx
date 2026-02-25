import { useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import { useVisualizerStore } from "@/stores/visualizer-store";
import { useAudioFeatures } from "@/hooks/use-audio-features";
import { ShaderScene } from "@/components/visualizer/scenes/shader-scene";

export function VisualizerCanvas() {
  const customShaderCode = useVisualizerStore((s) => s.customShaderCode);
  const setShaderError = useVisualizerStore((s) => s.setShaderError);
  const { features, beatState } = useAudioFeatures();

  const handleShaderError = useCallback(
    (error: string) => {
      console.warn("Shader compile error:", error);
      setShaderError(error);
    },
    [setShaderError],
  );

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 60 }}
      className="!absolute inset-0"
      gl={{ antialias: true, alpha: false }}
    >
      <color attach="background" args={["#000000"]} />
      <ShaderScene
        features={features}
        beatState={beatState}
        shaderCode={customShaderCode ?? ""}
        onCompileError={handleShaderError}
      />
    </Canvas>
  );
}
