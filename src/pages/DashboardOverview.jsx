import React from 'react';
import KpiCards from '../components/KpiCards';
import TrafficNetworkVisualizer from '../components/TrafficNetworkVisualizer';
import IntersectionDetailModal from '../components/IntersectionDetailModal';
import OptimizationPipeline from '../components/OptimizationPipeline';
import EmergencyCorridorPanel from '../components/EmergencyCorridorPanel';
import { useTraffic } from '../context/TrafficContext';
import { Sparkles, AlertTriangle, Cpu, Siren } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DashboardOverview() {
  const { activeEvents, isOptimized, emergencyCorridorActive } = useTraffic();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
      {/* Top Section: KPI Cards */}
      <section>
        <KpiCards />
      </section>

      {/* Main Grid: Left = Visualizer, Right = Inspector & Quick Controls */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.6fr 1fr',
        gap: '20px',
        minHeight: '560px',
      }}>
        {/* Left Column: Live Traffic Flow Graph */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <TrafficNetworkVisualizer />
        </div>

        {/* Right Column: Node Inspector & Optimization Quick Control */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <IntersectionDetailModal />
          <OptimizationPipeline />
          <EmergencyCorridorPanel />
        </div>
      </div>
    </div>
  );
}
