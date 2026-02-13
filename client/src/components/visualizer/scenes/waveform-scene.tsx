import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";
import { getFrequencyData } from "@/lib/audio-context";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
}

const BAR_COUNT = 64;

export function WaveformScene({ features, beatState }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const barsRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame(() => {
    if (!barsRef.current) return;

    const freqData = getFrequencyData();
    const rms = features?.rms ?? 0;
    const beatPulse = beatState.beatIntensity;

    // Sample frequency bins for our bar count
    const binStep = Math.floor(freqData.length / BAR_COUNT);

    for (let i = 0; i < BAR_COUNT; i++) {
      const binIdx = i * binStep;
      const value = (freqData[binIdx] ?? 0) / 255;
      const height = 0.1 + value * 3 + beatPulse * 0.5;

      const x = (i - BAR_COUNT / 2) * 0.15;
      dummy.position.set(x, height / 2 - 1, 0);
      dummy.scale.set(0.1, height, 0.1);
      dummy.updateMatrix();

      barsRef.current.setMatrixAt(i, dummy.matrix);

      // Color: gradient from purple (bass) to cyan (treble)
      const hue = 0.65 + (i / BAR_COUNT) * 0.3;
      const saturation = 0.7 + rms * 0.3;
      const lightness = 0.3 + value * 0.4;
      const color = new THREE.Color().setHSL(hue, saturation, lightness);
      barsRef.current.setColorAt(i, color);
    }

    barsRef.current.instanceMatrix.needsUpdate = true;
    if (barsRef.current.instanceColor) {
      barsRef.current.instanceColor.needsUpdate = true;
    }

    // Subtle group movement
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.0005) * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      <instancedMesh ref={barsRef} args={[undefined, undefined, BAR_COUNT]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          toneMapped={false}
          emissive="#7C5CFC"
          emissiveIntensity={0.2}
        />
      </instancedMesh>
    </group>
  );
}
