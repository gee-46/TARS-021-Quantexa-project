import { useState, useEffect } from 'react';
import WebThreads from './WebThreads';
import LetterGlitch from './LetterGlitch';
import { Streamlit } from './streamlit';
import './App.css';

const STAGES = [
  { time: 0, text: 'INITIALIZING QUANTUMFLOW', progress: 15 },
  { time: 700, text: 'INITIALIZING OPTIMIZATION ENGINE', progress: 40 },
  { time: 1400, text: 'LOADING TRAFFIC SIMULATOR', progress: 65 },
  { time: 2100, text: 'INITIALIZING EMERGENCY CONTROL', progress: 88 },
  { time: 2800, text: 'SYSTEM READY', progress: 100 },
];

export default function App() {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [visualMode, setVisualMode] = useState('threads'); // 'threads', 'glitch', 'fusion'

  useEffect(() => {
    // Notify Streamlit that component is ready and set frame height
    Streamlit.setComponentReady();
    Streamlit.setFrameHeight(window.innerHeight || 750);

    const handleResize = () => {
      Streamlit.setFrameHeight(window.innerHeight || 750);
    };
    window.addEventListener('resize', handleResize);

    // Sequence timers
    const timerIds = [];

    STAGES.forEach((stage, idx) => {
      if (idx > 0) {
        const id = setTimeout(() => {
          setCurrentStageIdx(idx);
        }, stage.time);
        timerIds.push(id);
      }
    });

    // Final completion trigger at ~3.2s
    const completionId = setTimeout(() => {
      Streamlit.setComponentValue('LOADER_COMPLETE');
    }, 3200);
    timerIds.push(completionId);

    return () => {
      timerIds.forEach(id => clearTimeout(id));
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const stage = STAGES[currentStageIdx] || STAGES[0];

  return (
    <div className="loader-root">
      {/* Background Visual Layer: WebThreads */}
      {(visualMode === 'threads' || visualMode === 'fusion') && (
        <WebThreads
          color1="#5227FF"
          color2="#FF9FFC"
          color3="#FFFFFF"
          speed={0.2}
          threadCount={6}
          frequency={5}
          spread={0.18}
          taper={1}
          position={0.5}
          fanMode="center"
          glow={0.02}
          falloff={0.6}
          thickness={1.1}
          brightness={0.6}
          opacity={1}
          mirror={true}
          shimmer={false}
          grain={true}
          grainIntensity={0.05}
          mouseInteraction={true}
          mouseStrength={0.3}
        />
      )}

      {/* Background Visual Layer: LetterGlitch from React Bits */}
      {(visualMode === 'glitch' || visualMode === 'fusion') && (
        <div className={`glitch-layer ${visualMode === 'fusion' ? 'fusion-mode' : 'pure-mode'}`}>
          <LetterGlitch
            glitchColors={['#2b4539', '#61dca3', '#61b3dc']}
            glitchSpeed={50}
            centerVignette={true}
            outerVignette={false}
            smooth={true}
            characters="01QUBOQAOAISINGSIMULATION"
          />
        </div>
      )}

      {/* Visual Mode Selector in Corner */}
      <div className="visual-mode-toggle">
        <button
          className={visualMode === 'threads' ? 'active' : ''}
          onClick={() => setVisualMode('threads')}
          title="WebThreads WebGL2"
        >
          Threads
        </button>
        <button
          className={visualMode === 'glitch' ? 'active' : ''}
          onClick={() => setVisualMode('glitch')}
          title="LetterGlitch Matrix"
        >
          Glitch
        </button>
        <button
          className={visualMode === 'fusion' ? 'active' : ''}
          onClick={() => setVisualMode('fusion')}
          title="Hybrid Fusion"
        >
          Fusion
        </button>
      </div>

      {/* Futuristic Center Overlay */}
      <div className="loader-overlay">
        <div className="quantum-badge">
          <span className="pulse-dot"></span>
          QUBO • QAOA • SIMULATION
        </div>

        <h1 className="loader-title">QUANTUMFLOW</h1>
        <p className="loader-subtitle">HYBRID QUANTUM-CLASSICAL TRAFFIC OPTIMIZATION</p>

        <div className="progress-container">
          <div
            className="progress-bar"
            style={{ width: `${stage.progress}%` }}
          />
        </div>

        <div className="status-line">
          {stage.progress === 100 ? (
            <span className="system-ready-check">✓ {stage.text}</span>
          ) : (
            <>
              <span className="status-spinner"></span>
              <span>{stage.text}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
