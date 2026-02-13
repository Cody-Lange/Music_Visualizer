import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
}

const STAR_COUNT = 200;
const SPEED_LINE_COUNT = 40;

/**
 * 90s Anime scene — warm cel-shaded look inspired by Evangelion,
 * Cowboy Bebop, Akira, Sailor Moon era aesthetics.
 *
 * Visual language: speed lines that burst on beats, a central glowing
 * orb with toon-shaded concentric rings, warm sunset palette
 * (amber/pink/deep indigo), starfield background, energy aura
 * that expands with bass.
 */
export function Anime90sScene({ features, beatState }: Props) {
  const orbRef = useRef<THREE.Mesh>(null);
  const auraRef = useRef<THREE.Mesh>(null);
  const auraMaterialRef = useRef<THREE.MeshBasicMaterial>(null);
  const ringsGroupRef = useRef<THREE.Group>(null);
  const starsRef = useRef<THREE.Points>(null);
  const starMaterialRef = useRef<THREE.PointsMaterial>(null);
  const speedLinesRef = useRef<THREE.LineSegments>(null);
  const speedLineMaterialRef = useRef<THREE.LineBasicMaterial>(null);

  // Starfield positions
  const starPositions = useMemo(() => {
    const arr = new Float32Array(STAR_COUNT * 3);
    for (let i = 0; i < STAR_COUNT; i++) {
      // Spread stars on a sphere shell
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 6 + Math.random() * 4;
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);

  // Speed line geometry — lines radiating outward from center
  const speedLineGeometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    const verts: number[] = [];

    for (let i = 0; i < SPEED_LINE_COUNT; i++) {
      const angle = (i / SPEED_LINE_COUNT) * Math.PI * 2;
      const innerR = 1.2 + Math.random() * 0.5;
      const outerR = 3 + Math.random() * 3;
      // Inner point
      verts.push(
        Math.cos(angle) * innerR,
        Math.sin(angle) * innerR,
        0,
      );
      // Outer point
      verts.push(
        Math.cos(angle) * outerR,
        Math.sin(angle) * outerR,
        0,
      );
    }

    geom.setAttribute(
      "position",
      new THREE.BufferAttribute(new Float32Array(verts), 3),
    );
    return geom;
  }, []);

  // Store base speed line positions for animation
  const baseSpeedPositions = useMemo(() => {
    const pos = speedLineGeometry.attributes.position;
    return pos ? Float32Array.from(pos.array as Float32Array) : new Float32Array(0);
  }, [speedLineGeometry]);

  useFrame((state, delta) => {
    const rms = features?.rms ?? 0;
    const bass = features?.energyBands.bass ?? 0;
    const mid = features?.energyBands.mid ?? 0;
    const treble = features?.energyBands.treble ?? 0;
    const beatPulse = beatState.beatIntensity;
    const time = state.clock.elapsedTime;

    // --- Central orb: warm glow, pulses with bass ---
    if (orbRef.current) {
      const orbScale = 0.8 + bass * 0.4 + beatPulse * 0.3;
      orbRef.current.scale.setScalar(orbScale);
      orbRef.current.rotation.y += delta * 0.5;
      orbRef.current.rotation.z += delta * 0.2;
    }

    // --- Aura: expanding energy ring ---
    if (auraRef.current && auraMaterialRef.current) {
      const auraScale = 1.5 + rms * 1.5 + beatPulse * 1.0;
      auraRef.current.scale.setScalar(auraScale);
      auraMaterialRef.current.opacity = 0.15 + beatPulse * 0.35 + bass * 0.15;

      // Color shift: amber → pink based on energy
      const hue = 0.05 + mid * 0.08; // warm range: 0.05 (amber) → 0.13 (pink-ish)
      auraMaterialRef.current.color.setHSL(hue, 0.9, 0.6);
    }

    // --- Concentric rings: rotate at different speeds ---
    if (ringsGroupRef.current) {
      const children = ringsGroupRef.current.children;
      for (let i = 0; i < children.length; i++) {
        const ring = children[i];
        if (!ring) continue;
        const speed = (i + 1) * 0.3;
        ring.rotation.z += delta * speed * (0.5 + rms);

        // Pulse scale on beat
        const ringScale = 1 + beatPulse * 0.15 * (i + 1) * 0.3;
        ring.scale.setScalar(ringScale);
      }
    }

    // --- Starfield: twinkle and slow rotation ---
    if (starsRef.current) {
      starsRef.current.rotation.y += delta * 0.02;
      starsRef.current.rotation.x += delta * 0.01;

      if (starMaterialRef.current) {
        // Twinkle by modulating size
        starMaterialRef.current.size = 0.04 + Math.sin(time * 3) * 0.015 + treble * 0.03;
        starMaterialRef.current.opacity = 0.5 + rms * 0.3;
      }
    }

    // --- Speed lines: burst on beats, fade out ---
    if (speedLinesRef.current && speedLineMaterialRef.current) {
      const pos = speedLinesRef.current.geometry.attributes.position;
      if (pos) {
        const arr = pos.array as Float32Array;
        for (let i = 0; i < SPEED_LINE_COUNT; i++) {
          const outerIdx = i * 6 + 3; // outer point x,y,z
          const baseX = baseSpeedPositions[outerIdx] ?? 0;
          const baseY = baseSpeedPositions[outerIdx + 1] ?? 0;

          // Extend outward on beat
          const extend = 1 + beatPulse * 2 + rms * 0.5;
          arr[outerIdx] = baseX * extend;
          arr[outerIdx + 1]! = baseY * extend;
        }
        pos.needsUpdate = true;
      }

      // Speed line visibility tied to beat
      speedLineMaterialRef.current.opacity = beatPulse * 0.7 + rms * 0.1;

      // Warm white / light pink color
      const lineHue = 0.08 + treble * 0.05;
      speedLineMaterialRef.current.color.setHSL(lineHue, 0.4, 0.9);
    }
  });

  // 90s anime warm palette
  const orbColor = "#FFA040"; // Amber/orange
  const ringColors = ["#FF6B8A", "#E8456B", "#C02050", "#8B1540"]; // Pink gradient

  return (
    <group>
      {/* Starfield background */}
      <points ref={starsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={STAR_COUNT}
            array={starPositions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          ref={starMaterialRef}
          size={0.05}
          color="#FFEEDD"
          transparent
          opacity={0.6}
          sizeAttenuation
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Speed lines — radial burst */}
      <lineSegments ref={speedLinesRef} geometry={speedLineGeometry}>
        <lineBasicMaterial
          ref={speedLineMaterialRef}
          color="#FFDDCC"
          transparent
          opacity={0}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      {/* Concentric rings */}
      <group ref={ringsGroupRef}>
        {ringColors.map((color, i) => (
          <mesh key={i} rotation={[0, 0, i * 0.4]}>
            <torusGeometry args={[1.2 + i * 0.45, 0.02, 8, 64]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={0.6}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        ))}
      </group>

      {/* Energy aura */}
      <mesh ref={auraRef}>
        <circleGeometry args={[1.2, 32]} />
        <meshBasicMaterial
          ref={auraMaterialRef}
          color="#FF8844"
          transparent
          opacity={0.2}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Central orb */}
      <mesh ref={orbRef}>
        <icosahedronGeometry args={[0.6, 2]} />
        <meshStandardMaterial
          color={orbColor}
          emissive={orbColor}
          emissiveIntensity={0.6}
        />
      </mesh>
    </group>
  );
}
