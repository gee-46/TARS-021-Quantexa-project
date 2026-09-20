import { useState, useEffect } from 'react';
import LetterGlitch from './LetterGlitch';
import './QuantumLoader.css';

// The QuantumFlow number-glitch loader (same visuals and timing as the Streamlit loader in
// frontend/webthreads), shown once per browser session on first load.
// Add ?loader=1 to the URL to replay it.

const STAGES = [
  { time: 0, text: 'INITIALIZING QUANTUMFLOW', progress: 15 },
  { time: 700, text: 'INITIALIZING OPTIMIZATION ENGINE', progress: 40 },
  { time: 1400, text: 'LOADING TRAFFIC SIMULATOR', progress: 65 },
  { time: 2100, text: 'INITIALIZING EMERGENCY CONTROL', progress: 88 },
  { time: 2800, text: 'SYSTEM READY', progress: 100 },
];
const DONE_AT = 3200;
const KEY = 'qf_loader_seen';

function shouldShow() {
  try {
    if (new URLSearchParams(window.location.search).get('loader') === '1') return true;
    return sessionStorage.getItem(KEY) !== '1';
  } catch {
    return true;
  }
}

export default function QuantumLoader() {
  const [visible, setVisible] = useState(shouldShow);
  const [fading, setFading] = useState(false);
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    if (!visible) return undefined;
    const ids = STAGES.slice(1).map((s, i) => setTimeout(() => setStageIdx(i + 1), s.time));
    ids.push(setTimeout(() => setFading(true), DONE_AT));
    ids.push(
      setTimeout(() => {
        try {
          sessionStorage.setItem(KEY, '1');
        } catch {
          /* storage unavailable: loader will simply show again next load */
        }
        setVisible(false);
      }, DONE_AT + 500),
    );
    return () => ids.forEach(clearTimeout);
  }, [visible]);

  if (!visible) return null;
  const stage = STAGES[stageIdx];

  return (
    <div
      role="status"
      aria-label="Loading QuantumFlow"
      style={{ position: 'fixed', inset: 0, zIndex: 10000, background: '#000', opacity: fading ? 0 : 1, transition: 'opacity 0.5s ease' }}
    >
      <div className="loader-root">
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

        <div className="loader-overlay">
          <div className="quantum-badge">
            <span className="pulse-dot"></span>
            QUBO • QAOA • SIMULATION
          </div>

          <h1 className="loader-title">QUANTUMFLOW</h1>
          <p className="loader-subtitle">HYBRID QUANTUM-CLASSICAL TRAFFIC OPTIMIZATION</p>

          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${stage.progress}%` }} />
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
    </div>
  );
}
