import { useEffect, useRef } from 'react';
import { Renderer, Program, Mesh, Triangle } from 'ogl';
import './WebThreads.css';

function hexToRgb(hex) {
  if (!hex) return [1.0, 1.0, 1.0];
  let clean = hex.replace(/^#/, '');
  if (clean.length === 3) {
    clean = clean.split('').map(c => c + c).join('');
  }
  const num = parseInt(clean, 16);
  return [
    ((num >> 16) & 255) / 255,
    ((num >> 8) & 255) / 255,
    (num & 255) / 255,
  ];
}

const vertexShader = `#version 300 es
in vec2 position;
in vec2 uv;
out vec2 vUv;

void main() {
    vUv = uv;
    gl_Position = vec4(position, 0.0, 1.0);
}
`;

const fragmentShader = `#version 300 es
precision highp float;

in vec2 vUv;
out vec4 fragColor;

uniform float uTime;
uniform vec2 uResolution;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform vec3 uColor3;
uniform float uSpeed;
uniform float uThreadCount;
uniform float uFrequency;
uniform float uSpread;
uniform float uTaper;
uniform float uPosition;
uniform float uFanMode;
uniform float uGlow;
uniform float uFalloff;
uniform float uThickness;
uniform float uBrightness;
uniform float uOpacity;
uniform float uMirror;
uniform float uShimmer;
uniform float uGrain;
uniform float uGrainIntensity;
uniform vec2 uMouse;
uniform float uMouseStrength;

float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    vec2 st = (gl_FragCoord.xy - 0.5 * uResolution.xy) / min(uResolution.x, uResolution.y);
    
    // Mouse interaction displacement
    vec2 m = uMouse * uMouseStrength;
    float distToMouse = length(st - m);
    vec2 mouseOffset = (st - m) / (distToMouse + 0.6) * exp(-distToMouse * 3.0) * uMouseStrength;
    st += mouseOffset;

    // Mirror mode
    if (uMirror > 0.5) {
        st.x = abs(st.x);
    }

    // Position & fan alignment
    float fanOffset = (uFanMode - 0.5) * 2.0;
    st.x += fanOffset * 0.15;
    st.y += (uPosition - 0.5) * 1.2;

    float t = uTime * uSpeed;
    
    vec3 finalColor = vec3(0.0);
    float totalAlpha = 0.0;
    float numThreads = max(1.0, uThreadCount);
    
    for (float i = 0.0; i < 16.0; i += 1.0) {
        if (i >= numThreads) break;

        float progress = i / max(1.0, numThreads - 1.0);
        float phaseOffset = i * uSpread * 3.14159265;
        
        // Taper factor
        float taperFactor = 1.0;
        if (uTaper > 0.0) {
            taperFactor = smoothstep(1.5, 0.0, abs(st.x) * uTaper);
        }

        // Dual sinusoidal wave displacement
        float wave1 = sin(st.x * uFrequency + t + phaseOffset) * 0.22 * taperFactor;
        float wave2 = cos(st.x * (uFrequency * 0.55) - t * 0.75 + phaseOffset * 1.3) * 0.12 * taperFactor;
        float curveY = wave1 + wave2;

        // Distance from current thread curve
        float dist = abs(st.y - curveY);

        // Line thickness and glow falloff
        float threadThick = uThickness * 0.004 * taperFactor;
        float intensity = threadThick / (pow(dist + 0.001, uFalloff * 2.0 + 0.45));
        intensity += exp(-dist * (1.0 / max(0.001, uGlow * 0.1))) * uGlow * 18.0;

        // Color interpolation: color1 -> color2 -> color3
        vec3 threadColor;
        if (progress < 0.5) {
            threadColor = mix(uColor1, uColor2, progress * 2.0);
        } else {
            threadColor = mix(uColor2, uColor3, (progress - 0.5) * 2.0);
        }

        // Shimmer modulation
        if (uShimmer > 0.5) {
            float sh = sin(t * 3.0 + i * 2.0 + st.x * 10.0) * 0.5 + 0.5;
            intensity *= (0.75 + 0.5 * sh);
        }

        finalColor += threadColor * intensity * uBrightness;
        totalAlpha += intensity * 0.5;
    }

    // Grain
    if (uGrain > 0.5) {
        float noise = hash(gl_FragCoord.xy + fract(uTime) * 100.0) * 2.0 - 1.0;
        finalColor += noise * uGrainIntensity;
    }

    finalColor *= uOpacity;
    float alpha = clamp(totalAlpha * uOpacity, 0.0, 1.0);

    fragColor = vec4(finalColor, alpha);
}
`;

export default function WebThreads({
  color1 = '#5227FF',
  color2 = '#FF9FFC',
  color3 = '#FFFFFF',
  speed = 0.2,
  threadCount = 6,
  frequency = 5,
  spread = 0.18,
  taper = 1,
  position = 0.5,
  fanMode = 'center',
  glow = 0.02,
  falloff = 0.6,
  thickness = 1.1,
  brightness = 0.6,
  opacity = 1,
  mirror = true,
  shimmer = false,
  grain = true,
  grainIntensity = 0.05,
  mouseInteraction = true,
  mouseStrength = 0.3,
}) {
  const containerRef = useRef(null);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });
  const isVisibleRef = useRef(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let renderer;
    try {
      renderer = new Renderer({
        alpha: true,
        premultipliedAlpha: false,
        antialias: true,
        webgl: 2,
      });
    } catch (e) {
      console.warn('WebGL2 not supported, falling back to WebGL1', e);
      renderer = new Renderer({
        alpha: true,
        premultipliedAlpha: false,
        antialias: true,
      });
    }

    const gl = renderer.gl;
    const canvas = gl.canvas;
    canvas.classList.add('webthreads-canvas');
    container.appendChild(canvas);

    const geometry = new Triangle(gl);

    // Fan mode mapping
    let fanVal = 0.5;
    if (fanMode === 'left') fanVal = 0.0;
    else if (fanMode === 'right') fanVal = 1.0;
    else if (typeof fanMode === 'number') fanVal = fanMode;

    const program = new Program(gl, {
      vertex: vertexShader,
      fragment: fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uResolution: { value: [container.clientWidth || 800, container.clientHeight || 600] },
        uColor1: { value: hexToRgb(color1) },
        uColor2: { value: hexToRgb(color2) },
        uColor3: { value: hexToRgb(color3) },
        uSpeed: { value: speed },
        uThreadCount: { value: threadCount },
        uFrequency: { value: frequency },
        uSpread: { value: spread },
        uTaper: { value: taper },
        uPosition: { value: position },
        uFanMode: { value: fanVal },
        uGlow: { value: glow },
        uFalloff: { value: falloff },
        uThickness: { value: thickness },
        uBrightness: { value: brightness },
        uOpacity: { value: opacity },
        uMirror: { value: mirror ? 1.0 : 0.0 },
        uShimmer: { value: shimmer ? 1.0 : 0.0 },
        uGrain: { value: grain ? 1.0 : 0.0 },
        uGrainIntensity: { value: grainIntensity },
        uMouse: { value: [0, 0] },
        uMouseStrength: { value: mouseStrength },
      },
      transparent: true,
    });

    const mesh = new Mesh(gl, { geometry, program });

    const handleResize = () => {
      if (!container) return;
      const width = container.clientWidth || window.innerWidth;
      const height = container.clientHeight || window.innerHeight;
      renderer.setSize(width, height);
      program.uniforms.uResolution.value = [width, height];
    };

    handleResize();

    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });
    resizeObserver.observe(container);

    const handleMouseMove = (e) => {
      if (!mouseInteraction || !container) return;
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      mouseRef.current.targetX = x;
      mouseRef.current.targetY = y;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleVisibilityChange = () => {
      isVisibleRef.current = document.visibilityState === 'visible';
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    const intersectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        isVisibleRef.current = entry.isIntersecting;
      });
    });
    intersectionObserver.observe(container);

    let animationFrameId;
    let lastTime = performance.now();

    const update = (now) => {
      animationFrameId = requestAnimationFrame(update);

      if (!isVisibleRef.current) return;

      const delta = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // Mouse smooth interpolation
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      program.uniforms.uTime.value = now * 0.001;
      program.uniforms.uMouse.value = [mouseRef.current.x, mouseRef.current.y];

      renderer.render({ scene: mesh });
    };

    animationFrameId = requestAnimationFrame(update);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    };
  }, [
    color1,
    color2,
    color3,
    speed,
    threadCount,
    frequency,
    spread,
    taper,
    position,
    fanMode,
    glow,
    falloff,
    thickness,
    brightness,
    opacity,
    mirror,
    shimmer,
    grain,
    grainIntensity,
    mouseInteraction,
    mouseStrength,
  ]);

  return <div ref={containerRef} className="webthreads-container" />;
}
