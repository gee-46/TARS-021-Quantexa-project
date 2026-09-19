import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopStatusBar from './TopStatusBar';

export default function DashboardLayout() {
  return (
    <div style={{
      display: 'flex',
      width: '100vw',
      height: '100vh',
      background: '#070612',
      color: '#f8fafc',
      overflow: 'hidden',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Viewport */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        position: 'relative',
      }}>
        <TopStatusBar />

        <main style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          background: 'radial-gradient(ellipse at 50% 0%, rgba(20, 15, 45, 0.6) 0%, rgba(7, 6, 18, 0.95) 70%)',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
