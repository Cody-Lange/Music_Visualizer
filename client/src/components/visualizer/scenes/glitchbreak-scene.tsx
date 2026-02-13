import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
}

const PARTICLE_COUNT = 600;
const GRID_SIZE = 12;

/**
 * Glitchbreak scene — inspired by Sewerslvt / breakcore aesthetics.
 *
 * Visual language: chaotic digital decay, VHS corruption, neon-on-black,
 * rapid positional jitter on beats, RGB channel splitting, broken grid
 * geometry that fragments with percussive energy.
 */
export function GlitchbreakScene({ features, beatState }: Props) {
  const particlesRef = useRef<THREE.Points>(null);
  const particleMaterialRef = useRef<THREE.PointsMaterial>(null);
  const gridRef = useRef<THREE.LineSegments>(null);
  const gridMaterialRef = useRef<THREE.LineBasicMaterial>(null);
  const rgbGroupRef = useRef<THREE.Group>(null);
  const glitchOffsetRef = useRef(0);

  // Scattered particle field
  const positions = useMemo(() => {
    const arr = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 12;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 12;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 8;
    }
    return arr;
  }, []);

  // Distorted grid geometry — lines that can be jittered
  const gridGeometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    const verts: number[] = [];
    const half = GRID_SIZE / 2;
    const step = 1;

    // Horizontal lines
    for (let y = -half; y <= half; y += step) {
      verts.push(-half, y, 0, half, y, 0);
    }
    // Vertical lines
    for (let x = -half; x <= half; x += step) {
      verts.push(x, -half, 0, x, half, 0);
    }

    geom.setAttribute(
      "position",
      new THREE.BufferAttribute(new Float32Array(verts), 3),
    );
    return geom;
  }, []);

  // Store base grid positions for glitch displacement
  const baseGridPositions = useMemo(() => {
    const pos = gridGeometry.attributes.position;
    return pos ? Float32Array.from(pos.array as Float32Array) : new Float32Array(0);
  }, [gridGeometry]);

  useFrame((state, delta) => {
    const rms = features?.rms ?? 0;
    const bass = features?.energyBands.bass ?? 0;
    const treble = features?.energyBands.treble ?? 0;
    const percussive = features?.percussiveEnergy ?? 0;
    const beatPulse = beatState.beatIntensity;
    const time = state.clock.elapsedTime;

    // --- Glitch offset: sharp displacement on beats ---
    if (beatState.isOnBeat) {
      glitchOffsetRef.current = (Math.random() - 0.5) * 0.4 * beatPulse;
    } else {
      glitchOffsetRef.current *= 0.85; // Rapid decay
    }

    // --- Particles: chaotic jitter ---
    if (particlesRef.current) {
      const pos = particlesRef.current.geometry.attributes.position;
      if (pos) {
        const arr = pos.array as Float32Array;
        for (let i = 0; i < PARTICLE_COUNT; i++) {
          const i3 = i * 3;
          // Constant drift
          arr[i3]! += Math.sin(time * 2 + i) * delta * 0.3;
          arr[i3 + 1]! += Math.cos(time * 1.5 + i * 0.7) * delta * 0.3;

          // Beat-triggered scatter
          if (beatState.isOnBeat && Math.random() < 0.3) {
            arr[i3]! += (Math.random() - 0.5) * percussive * 2;
            arr[i3 + 1]! += (Math.random() - 0.5) * percussive * 2;
          }

          // Wrap
          for (let j = 0; j < 3; j++) {
            if (arr[i3 + j]! > 6) arr[i3 + j]! = -6;
            if (arr[i3 + j]! < -6) arr[i3 + j]! = 6;
          }
        }
        pos.needsUpdate = true;
      }

      // Color flicker between hot pink and cyan
      if (particleMaterialRef.current) {
        const flicker = Math.sin(time * 15) > 0;
        particleMaterialRef.current.color.set(
          flicker ? "#FF0066" : "#00FFFF",
        );
        particleMaterialRef.current.size = 0.03 + beatPulse * 0.12 + rms * 0.04;
        particleMaterialRef.current.opacity = 0.5 + rms * 0.5;
      }
    }

    // --- Grid: VHS-style distortion ---
    if (gridRef.current) {
      const pos = gridRef.current.geometry.attributes.position;
      if (pos) {
        const arr = pos.array as Float32Array;
        for (let i = 0; i < arr.length; i += 3) {
          // Reset to base
          arr[i] = baseGridPositions[i] ?? 0;
          arr[i + 1] = baseGridPositions[i + 1] ?? 0;
          arr[i + 2] = baseGridPositions[i + 2] ?? 0;

          // Horizontal scanline displacement (VHS tracking error)
          const scanlinePhase = Math.sin(
            (arr[i + 1]! * 3 + time * 8) * 2,
          );
          arr[i]! += scanlinePhase * bass * 0.3;

          // Beat-triggered glitch blocks
          if (beatPulse > 0.1) {
            const blockY = Math.floor(arr[i + 1]! * 2);
            if (blockY % 3 === 0) {
              arr[i]! += glitchOffsetRef.current * 3;
            }
          }

          // Z-depth jitter from percussive energy
          arr[i + 2]! += Math.sin(time * 5 + i * 0.3) * percussive * 0.5;
        }
        pos.needsUpdate = true;
      }

      // Grid color oscillates
      if (gridMaterialRef.current) {
        const hue = (time * 0.1) % 1;
        const saturation = 0.8 + treble * 0.2;
        gridMaterialRef.current.color.setHSL(hue, saturation, 0.4 + rms * 0.3);
        gridMaterialRef.current.opacity = 0.2 + bass * 0.5 + beatPulse * 0.3;
      }

      // Slow rotation
      gridRef.current.rotation.z += delta * 0.03;
      gridRef.current.rotation.x = Math.sin(time * 0.15) * 0.2;
    }

    // --- RGB split effect: offset the entire group on beats ---
    if (rgbGroupRef.current) {
      rgbGroupRef.current.position.x = glitchOffsetRef.current;
      rgbGroupRef.current.position.y = glitchOffsetRef.current * 0.5;
    }
  });

  return (
    <group ref={rgbGroupRef}>
      {/* Glitch grid */}
      <lineSegments ref={gridRef} geometry={gridGeometry}>
        <lineBasicMaterial
          ref={gridMaterialRef}
          color="#FF0066"
          transparent
          opacity={0.4}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      {/* Particle scatter */}
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={PARTICLE_COUNT}
            array={positions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          ref={particleMaterialRef}
          size={0.05}
          color="#FF0066"
          transparent
          opacity={0.7}
          sizeAttenuation
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>
    </group>
  );
}
