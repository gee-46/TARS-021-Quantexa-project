import React from 'react';
import ReactDOM from 'react-dom/client';
import BorderGlow from './BorderGlow';
import './BorderGlow.css';

// The map HTML will be injected into a div with id="map-container" later by Streamlit.
const App = () => (
  <BorderGlow
    edgeSensitivity={30}
    glowColor="40 80 80"
    backgroundColor="#120F17"
    borderRadius={28}
    glowRadius={40}
    glowIntensity={1.0}
    coneSpread={25}
    animated={false}
    colors={["#c084fc", "#f472b6", "#38bdf8"]}
  >
    <div id="map-container" dangerouslySetInnerHTML={{ __html: window.mapHtml || '' }} />
  </BorderGlow>
);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
