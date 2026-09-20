import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopStatusBar from './TopStatusBar';

export default function DashboardLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)', overflow: 'hidden' }}>
      <TopStatusBar />
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <Sidebar />
        <main style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
