import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
}

const PARTICLE_COUNT = 800;

export function NebulaScene({ features, beatState }: Props) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.PointsMaterial>(null);

  const positions = useMemo(() => {
    const arr = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 10;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 10;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 10;
    }
    return arr;
  }, []);

  const velocities = useMemo(() => {
    const arr = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 0.01;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 0.01;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 0.01;
    }
    return arr;
  }, []);

  useFrame((state, delta) => {
    if (!pointsRef.current) return;
    const geom = pointsRef.current.geometry;
    const pos = geom.attributes.position;
    if (!pos) return;
    const arr = pos.array as Float32Array;

    const rms = features?.rms ?? 0;
    const bass = features?.energyBands.bass ?? 0;
    const beatPulse = beatState.beatIntensity;

    // Animate particles
    const speed = 0.5 + rms * 3 + beatPulse * 2;
    const time = state.clock.elapsedTime;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      arr[i3]! += (velocities[i3] ?? 0) * speed * delta * 60;
      arr[i3 + 1]! += (velocities[i3 + 1] ?? 0) * speed * delta * 60;
      arr[i3 + 2]! += (velocities[i3 + 2] ?? 0) * speed * delta * 60;

      // Add some swirl
      arr[i3]! += Math.sin(time * 0.3 + i * 0.1) * bass * delta * 0.5;
      arr[i3 + 1]! += Math.cos(time * 0.2 + i * 0.15) * bass * delta * 0.5;

      // Wrap around boundaries
      for (let j = 0; j < 3; j++) {
        if (arr[i3 + j]! > 5) arr[i3 + j]! = -5;
        if (arr[i3 + j]! < -5) arr[i3 + j]! = 5;
      }
    }

    pos.needsUpdate = true;

    // Pulse point size on beat
    if (materialRef.current) {
      materialRef.current.size = 0.04 + beatPulse * 0.08 + rms * 0.03;
      materialRef.current.opacity = 0.6 + rms * 0.4;
    }

    // Slow rotation
    pointsRef.current.rotation.y += delta * 0.05;
    pointsRef.current.rotation.x += delta * 0.02;
  });

  // Color based on spectral centroid
  const color = useMemo(() => {
    const centroid = features?.spectralCentroid ?? 0.5;
    // Map centroid to a hue: low = warm purple, high = cool blue
    const hue = 0.65 + centroid * 0.2;
    return new THREE.Color().setHSL(hue, 0.8, 0.6);
  }, [features?.spectralCentroid]);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={PARTICLE_COUNT}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.04}
        color={color}
        transparent
        opacity={0.7}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}
