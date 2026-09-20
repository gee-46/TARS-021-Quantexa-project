import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TrafficProvider } from './context/TrafficContext';
import DashboardLayout from './components/DashboardLayout';
import LiveTrafficPage from './pages/LiveTrafficPage';
import TrafficNetworkPage from './pages/TrafficNetworkPage';
import QuantumOptimizerPage from './pages/QuantumOptimizerPage';
import EmergencyCorridorPage from './pages/EmergencyCorridorPage';
import EventsPage from './pages/EventsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ClassicalComparisonPage from './pages/ClassicalComparisonPage';
import ArchitecturePage from './pages/ArchitecturePage';
import MapPage from './pages/MapPage';
import GraphPage from './pages/GraphPage';
import QuantumLoader from './components/loader/QuantumLoader';

function App() {
  return (
    <TrafficProvider>
      <QuantumLoader />
      <BrowserRouter>
        <Routes>
          {/* Urban Traffic Operations Center: the live traffic scenario is the front page */}
          <Route element={<DashboardLayout />}>
            <Route path="/" element={<LiveTrafficPage />} />
            <Route path="/dashboard" element={<LiveTrafficPage />} />
            <Route path="/traffic" element={<TrafficNetworkPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/quantum" element={<QuantumOptimizerPage />} />
            <Route path="/emergency" element={<EmergencyCorridorPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/comparison" element={<ClassicalComparisonPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
          </Route>

          {/* Catch-all redirect to the live traffic screen */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </TrafficProvider>
  );
}

export default App;
