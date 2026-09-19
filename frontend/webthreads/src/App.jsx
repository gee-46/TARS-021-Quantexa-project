import { useState, useEffect } from 'react';
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
      {/* Background Visual: LetterGlitch from React Bits */}
      <div className="glitch-background">
        <LetterGlitch
          glitchColors={['#2b4539', '#61dca3', '#61b3dc']}
          glitchSpeed={50}
          centerVignette={true}
          outerVignette={false}
          smooth={true}
          characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$&*()-_+=/[]{};:<>.,0123456789"
        />
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
