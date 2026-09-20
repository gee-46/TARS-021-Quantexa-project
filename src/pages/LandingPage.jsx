import React, { useRef, useState } from 'react';
import Orb from '../components/Orb.jsx';
import AcidSquares from '../components/AcidSquares.jsx';
import DepthText from '../components/DepthText.jsx';
import VariableProximity from '../components/VariableProximity.jsx';
import TopStatusBar from '../components/TopStatusBar.jsx';
import DashboardOverview from './DashboardOverview.jsx';
import TrafficNetworkPage from './TrafficNetworkPage.jsx';
import QuantumOptimizerPage from './QuantumOptimizerPage.jsx';
import EmergencyCorridorPage from './EmergencyCorridorPage.jsx';
import EventsPage from './EventsPage.jsx';
import AnalyticsPage from './AnalyticsPage.jsx';
import ClassicalComparisonPage from './ClassicalComparisonPage.jsx';
import ArchitecturePage from './ArchitecturePage.jsx';
import MapPage from './MapPage.jsx';
import GraphPage from './GraphPage.jsx';
import {
  ArrowDown,
  ArrowUp,
  Sparkles,
  LayoutDashboard,
  Network,
  Cpu,
  Siren,
  AlertTriangle,
  BarChart3,
  GitCompare,
  Layers,
  Map,
  Share2,
} from 'lucide-react';

const tabs = [
  { id: 'overview', label: 'Command Overview', icon: LayoutDashboard, component: DashboardOverview },
  { id: 'traffic', label: 'Traffic Network', icon: Network, component: TrafficNetworkPage },
  { id: 'map', label: 'Corridor Map', icon: Map, component: MapPage },
  { id: 'graph', label: 'Network Graph', icon: Share2, component: GraphPage },
  { id: 'quantum', label: 'Quantum Optimizer', icon: Cpu, component: QuantumOptimizerPage },
  { id: 'emergency', label: 'Emergency Corridor', icon: Siren, component: EmergencyCorridorPage },
  { id: 'events', label: 'Scenarios & Events', icon: AlertTriangle, component: EventsPage },
  { id: 'analytics', label: 'Analytics & Trade-offs', icon: BarChart3, component: AnalyticsPage },
  { id: 'comparison', label: 'Solver Comparison', icon: GitCompare, component: ClassicalComparisonPage },
  { id: 'architecture', label: 'System Architecture', icon: Layers, component: ArchitecturePage },
];

export default function LandingPage() {
  const contentContainerRef = useRef(null);
  const [activeTab, setActiveTab] = useState('overview');

  const scrollToControlCenter = () => {
    document.getElementById('traffic-control-center')?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const ActiveComponent = tabs.find((t) => t.id === activeTab)?.component || DashboardOverview;

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

              {/* Primary Launcher CTA */}
              <div style={{ marginTop: '28px', pointerEvents: 'auto' }}>
                <button
                  onClick={scrollToControlCenter}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: 'linear-gradient(135deg, #5227FF 0%, #A855F7 100%)',
                    color: '#ffffff',
                    padding: '15px 30px',
                    borderRadius: '12px',
                    fontWeight: 800,
                    fontSize: '0.95rem',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                    cursor: 'pointer',
                    boxShadow: '0 0 32px rgba(168, 85, 247, 0.65), 0 4px 16px rgba(0, 0, 0, 0.5)',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-3px) scale(1.04)';
                    e.currentTarget.style.boxShadow = '0 0 45px rgba(168, 85, 247, 0.9), 0 8px 24px rgba(0, 0, 0, 0.6)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                    e.currentTarget.style.boxShadow = '0 0 32px rgba(168, 85, 247, 0.65), 0 4px 16px rgba(0, 0, 0, 0.5)';
                  }}
                >
                  <Sparkles size={18} />
                  <span>LAUNCH TRAFFIC CONTROL CENTER</span>
                  <ArrowDown size={18} />
                </button>
              </div>

            </div>
          </div>
        </div>

        {/* Subtle Bottom Scroll Cue */}
        <div
          onClick={scrollToControlCenter}
          style={{
            position: 'absolute',
            bottom: '24px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 10,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            color: 'rgba(196, 181, 253, 0.7)',
            fontSize: '0.72rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            animation: 'pulseSlow 2s infinite',
          }}
        >
          <span>Scroll to the Control Center</span>
          <ArrowDown size={16} color="#a855f7" />
        </div>
      </section>

      {/* ========================================================== */}
      {/* SECTION 2: LIVE TRAFFIC CONTROL CENTER ON THE SAME PAGE    */}
      {/* ========================================================== */}
      <section
        id="traffic-control-center"
        style={{
          width: '100vw',
          minHeight: '100vh',
          background: 'radial-gradient(ellipse at 50% 0%, rgba(20, 15, 45, 0.98) 0%, rgba(6, 5, 15, 0.99) 100%)',
          borderTop: '1px solid rgba(139, 92, 246, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          zIndex: 20,
        }}
      >
        {/* Control Center Status Bar */}
        <TopStatusBar />

        {/* Interactive Module Navigation Bar */}
        <div style={{
          background: 'rgba(12, 10, 26, 0.95)',
          borderBottom: '1px solid rgba(139, 92, 246, 0.15)',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          overflowX: 'auto',
          gap: '12px',
          backdropFilter: 'blur(16px)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'nowrap' }}>
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 14px',
                    borderRadius: '8px',
                    fontSize: '0.8rem',
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? '#ffffff' : 'rgba(216, 207, 247, 0.75)',
                    background: isActive
                      ? 'linear-gradient(90deg, rgba(82, 39, 255, 0.35) 0%, rgba(168, 85, 247, 0.25) 100%)'
                      : 'rgba(255, 255, 255, 0.03)',
                    border: isActive
                      ? '1px solid rgba(168, 85, 247, 0.5)'
                      : '1px solid rgba(139, 92, 246, 0.12)',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.18s ease',
                  }}
                >
                  <Icon size={15} color={isActive ? '#00f5ff' : '#a855f7'} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={scrollToTop}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '8px',
              fontSize: '0.78rem',
              fontWeight: 700,
              color: '#c4b5fd',
              background: 'rgba(82, 39, 255, 0.15)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            <ArrowUp size={14} />
            <span>Top Launcher</span>
          </button>
        </div>

        {/* Dynamic Active Module Container */}
        <div style={{
          flex: 1,
          padding: '24px',
          maxWidth: '1600px',
          width: '100%',
          margin: '0 auto',
        }}>
          <ActiveComponent />
        </div>
      </section>

    </div>
  );
}
