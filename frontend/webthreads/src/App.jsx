import { useState, useEffect } from 'react';
import LetterGlitch from './LetterGlitch';
import { Streamlit } from './streamlit';
import './App.css';

export default function App() {
  useEffect(() => {
    Streamlit.setComponentReady();
    Streamlit.setFrameHeight(window.innerHeight || 750);

    const handleResize = () => {
      Streamlit.setFrameHeight(window.innerHeight || 750);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', margin: 0, padding: 0, overflow: 'hidden', backgroundColor: '#000000' }}>
      <LetterGlitch
        glitchSpeed={50}
        centerVignette={true}
        outerVignette={false}
        smooth={true}
        glitchColors={['#2b4539', '#61dca3', '#61b3dc']}
        characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$&*()-_+=/[]{};:<>.,0123456789"
      />
    </div>
  );
}
