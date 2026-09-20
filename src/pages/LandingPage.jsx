import React, { useRef } from 'react';
import { Link } from 'react-router-dom';
import Orb from '../components/Orb.jsx';
import AcidSquares from '../components/AcidSquares.jsx';
import DepthText from '../components/DepthText.jsx';
import VariableProximity from '../components/VariableProximity.jsx';

export default function LandingPage() {
  const contentContainerRef = useRef(null);

  return (
    <div style={{
      width: '100vw',
      minHeight: '100vh',
      background: '#06050f',
      position: 'relative',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    }}>

      {/* ========================================================== */}
      {/* SECTION 1: PRESERVED 3D ORB LAUNCHER HERO EXPERIENCE       */}
      {/* ========================================================== */}
      <section style={{
        width: '100vw',
        height: '100vh',
        position: 'relative',
        overflow: 'hidden',
        background: '#000',
      }}>
        {/* Layer 0 — AcidSquares full-screen background */}
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <AcidSquares
            color1="#5227FF"
            color2="#A855F7"
            color3="#FFFFFF"
            detail="medium"
            speed={0.7}
            waveDepth={1}
            zoom={1.3}
            density={10.0}
            glow={1.0}
            exposure={2700}
            spread={0.3}
            stepSize={0.002}
            colorShift={0}
            contrast={1}
            brightness={1.0}
            opacity={1.0}
            mouseInteraction={true}
            mouseStrength={0.1}
            mouseRadius={0.35}
            blur={0}
            grain={true}
            grainIntensity={0.05}
          />
        </div>

        {/* Center Stage — Orb with DepthText, Description & Primary CTA */}
        <div style={{
          position: 'absolute',
          inset: 0,
          zIndex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {/* Orb & Content Container */}
          <div style={{
            width: '850px',
            height: '850px',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {/* Interactive Orb */}
            <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
              <Orb
                hoverIntensity={0.29}
                rotateOnHover={true}
                hue={356}
                forceHoverState={false}
                backgroundColor="#000000"
              />
            </div>

            {/* Central Overlay Content */}
            <div
              ref={contentContainerRef}
              style={{
                position: 'relative',
                zIndex: 2,
                pointerEvents: 'auto',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                maxWidth: '620px',
                padding: '0 24px',
                userSelect: 'none',
              }}
            >
              {/* 3D Depth Title */}
              <DepthText
                text="QuantumForce"
                layers={38}
                depth={2.8}
                faceColor="#ffffff"
                depthColor="#4b37f8"
                tilt={8}
                pointerTracking
                smoothing={0.14}
                perspective={900}
                autoOrbit
                orbitSpeed={0.35}
                fontSize="clamp(3.2rem, 6.5vw, 5rem)"
                fontWeight={900}
                shadow
              />

              {/* VariableProximity Interactive Paragraphs */}
              <div style={{
                marginTop: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                color: 'rgba(240, 245, 255, 0.96)',
                fontSize: 'clamp(1.05rem, 1.65vw, 1.28rem)',
                lineHeight: 1.62,
                textShadow: '0 2px 12px rgba(0, 0, 0, 0.95), 0 0 26px rgba(75, 55, 248, 0.45)',
              }}>
                <div>
                  <VariableProximity
                    label="A hybrid quantum-classical traffic optimisation simulator that plans signal timing across connected junctions and measures waiting time, person-delay, fairness and idling CO₂ in simulation."
                    fromFontVariationSettings="'wght' 350, 'opsz' 14"
                    toFontVariationSettings="'wght' 950, 'opsz' 40"
                    containerRef={contentContainerRef}
                    radius={110}
                    falloff="gaussian"
                  />
                </div>

                <div style={{ color: 'rgba(220, 232, 255, 0.88)' }}>
                  <VariableProximity
                    label="It also simulates emergency green corridors, resolves conflicts between ambulances with a small QUBO, and shows what preemption costs everyone else."
                    fromFontVariationSettings="'wght' 350, 'opsz' 14"
                    toFontVariationSettings="'wght' 950, 'opsz' 40"
                    containerRef={contentContainerRef}
                    radius={110}
                    falloff="gaussian"
                  />
                </div>
              </div>

              {/* Entry point to the control center */}
              <div style={{ marginTop: '28px', pointerEvents: 'auto' }}>
                <Link
                  to="/dashboard"
                  style={{
                    display: 'inline-block',
                    background: '#5227FF',
                    color: '#ffffff',
                    padding: '12px 26px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    fontSize: '0.9rem',
                    textDecoration: 'none',
                  }}
                >
                  Open control center
                </Link>
              </div>

            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
