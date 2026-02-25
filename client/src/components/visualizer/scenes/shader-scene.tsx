import { useRef, useMemo, useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { AudioFeaturesAtTime, BeatState } from "@/types/audio";

interface Props {
  features: AudioFeaturesAtTime | null;
  beatState: BeatState;
  shaderCode: string;
  onCompileError?: (error: string) => void;
}

const VERTEX_SHADER = `
void main() {
  gl_Position = vec4(position, 1.0);
}
`;

/**
 * Wraps LLM-generated Shadertoy-compatible GLSL (mainImage function)
 * into a complete WebGL fragment shader with audio-reactive uniforms.
 */
function buildFragmentShader(userCode: string): string {
  return `precision highp float;

uniform float iTime;
uniform vec2 iResolution;
uniform float u_bass;
uniform float u_lowMid;
uniform float u_mid;
uniform float u_highMid;
uniform float u_treble;
uniform float u_energy;
uniform float u_beat;
uniform float u_spectralCentroid;

${userCode}

void main() {
  mainImage(gl_FragColor, gl_FragCoord.xy);
}
`;
}

/** Fallback shader — gentle audio-reactive plasma */
const FALLBACK_SHADER = `
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
  return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
  vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
  float t = iTime * 0.3;

  float d = length(uv);
  float angle = atan(uv.y, uv.x);

  // Audio-reactive warping
  uv += sin(uv.yx * 3.0 + t + u_bass * 2.0) * (0.3 + u_energy * 0.5);
  d = length(uv);

  // Concentric rings that pulse with bass
  float rings = sin(d * 8.0 - t * 2.0 + u_bass * 6.0) * 0.5 + 0.5;

  // Color from spectral centroid
  vec3 col = palette(
    d + t * 0.2 + u_spectralCentroid,
    vec3(0.5, 0.5, 0.5),
    vec3(0.5, 0.5, 0.5),
    vec3(1.0, 0.7, 0.4),
    vec3(0.0, 0.15, 0.2)
  );

  col *= rings;
  col += vec3(0.1, 0.05, 0.15) * u_treble * 3.0;

  // Beat flash
  col += vec3(0.3) * u_beat;

  // Vignette
  float vig = 1.0 - smoothstep(0.4, 1.4, length((fragCoord / iResolution.xy - 0.5) * 2.0));
  col *= vig;

  fragColor = vec4(col, 1.0);
}
`;

export function ShaderScene({ features, beatState, shaderCode, onCompileError }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const errorCheckedRef = useRef(false);
  const { size } = useThree();

  const uniforms = useMemo(
    () => ({
      iTime: { value: 0 },
      iResolution: { value: new THREE.Vector2(size.width, size.height) },
      u_bass: { value: 0 },
      u_lowMid: { value: 0 },
      u_mid: { value: 0 },
      u_highMid: { value: 0 },
      u_treble: { value: 0 },
      u_energy: { value: 0 },
      u_beat: { value: 0 },
      u_spectralCentroid: { value: 0.5 },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // Build and validate the shader material
  const shaderMaterial = useMemo(() => {
    const codeToUse = shaderCode || FALLBACK_SHADER;
    const fragmentShader = buildFragmentShader(codeToUse);

    try {
      return new THREE.ShaderMaterial({
        vertexShader: VERTEX_SHADER,
        fragmentShader,
        uniforms,
        depthWrite: false,
        depthTest: false,
      });
    } catch {
      // If construction fails, fall back
      const fallbackFrag = buildFragmentShader(FALLBACK_SHADER);
      return new THREE.ShaderMaterial({
        vertexShader: VERTEX_SHADER,
        fragmentShader: fallbackFrag,
        uniforms,
        depthWrite: false,
        depthTest: false,
      });
    }
  }, [shaderCode, uniforms]);

  useEffect(() => {
    materialRef.current = shaderMaterial;
    errorCheckedRef.current = false;
  }, [shaderMaterial]);

  // Update resolution when size changes
  useEffect(() => {
    uniforms.iResolution.value.set(size.width, size.height);
  }, [size, uniforms]);

  useFrame((state) => {
    const mat = materialRef.current;
    if (!mat) return;

    // Check for compile errors once after first render
    if (!errorCheckedRef.current) {
      errorCheckedRef.current = true;
      const gl = state.gl;
      const glContext = gl.getContext();
      // Use diagnostic extension to detect shader errors
      const ext = glContext.getExtension("WEBGL_debug_shaders");
      if (ext && onCompileError) {
        // Three.js compiles shaders lazily; errors surface via console.
        // We do a lightweight check by looking at the GL error state.
        const err = glContext.getError();
        if (err !== glContext.NO_ERROR) {
          onCompileError("WebGL shader compilation error (code " + err + ")");
        }
      }
    }

    mat.uniforms.iTime!.value = state.clock.elapsedTime;
    mat.uniforms.iResolution!.value.set(size.width, size.height);

    if (features) {
      mat.uniforms.u_bass!.value = features.energyBands.bass;
      mat.uniforms.u_lowMid!.value = features.energyBands.lowMid;
      mat.uniforms.u_mid!.value = features.energyBands.mid;
      mat.uniforms.u_highMid!.value = features.energyBands.highMid;
      mat.uniforms.u_treble!.value = features.energyBands.treble;
      mat.uniforms.u_energy!.value = features.rms;
      mat.uniforms.u_spectralCentroid!.value = features.spectralCentroid;
    }

    mat.uniforms.u_beat!.value = beatState.beatIntensity;
  });

  return (
    <mesh ref={meshRef} frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <primitive object={shaderMaterial} attach="material" />
    </mesh>
  );
}
