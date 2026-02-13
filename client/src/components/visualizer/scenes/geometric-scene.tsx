import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
}

export function GeometricScene({ features, beatState }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const torusRef = useRef<THREE.Mesh>(null);
  const icoRef = useRef<THREE.Mesh>(null);
  const octaRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    const rms = features?.rms ?? 0;
    const bass = features?.energyBands.bass ?? 0;
    const mid = features?.energyBands.mid ?? 0;
    const treble = features?.energyBands.treble ?? 0;
    const beatPulse = beatState.beatIntensity;
    const time = state.clock.elapsedTime;

    // Group rotation
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * (0.2 + rms * 0.5);
      groupRef.current.rotation.x = Math.sin(time * 0.1) * 0.3;
    }

    // Torus — driven by bass
    if (torusRef.current) {
      const scale = 1 + bass * 0.5 + beatPulse * 0.3;
      torusRef.current.scale.setScalar(scale);
      torusRef.current.rotation.x += delta * (0.5 + bass);
      torusRef.current.rotation.z += delta * 0.3;
    }

    // Icosahedron — driven by mids
    if (icoRef.current) {
      const scale = 0.6 + mid * 0.4 + beatPulse * 0.2;
      icoRef.current.scale.setScalar(scale);
      icoRef.current.rotation.y += delta * (0.3 + mid * 0.8);
      icoRef.current.rotation.z += delta * 0.2;
    }

    // Octahedron — driven by treble
    if (octaRef.current) {
      const scale = 0.4 + treble * 0.5 + beatPulse * 0.15;
      octaRef.current.scale.setScalar(scale);
      octaRef.current.rotation.x += delta * (0.4 + treble * 1.2);
      octaRef.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Torus — bass reactive */}
      <mesh ref={torusRef} position={[0, 0, 0]}>
        <torusGeometry args={[1.5, 0.05, 16, 100]} />
        <meshStandardMaterial
          color="#7C5CFC"
          wireframe
          emissive="#7C5CFC"
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* Icosahedron — mid reactive */}
      <mesh ref={icoRef} position={[0, 0, 0]}>
        <icosahedronGeometry args={[0.8, 1]} />
        <meshStandardMaterial
          color="#9B7FFF"
          wireframe
          emissive="#9B7FFF"
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* Octahedron — treble reactive */}
      <mesh ref={octaRef} position={[0, 0, 0]}>
        <octahedronGeometry args={[0.5, 0]} />
        <meshStandardMaterial
          color="#34D399"
          wireframe
          emissive="#34D399"
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  );
}
