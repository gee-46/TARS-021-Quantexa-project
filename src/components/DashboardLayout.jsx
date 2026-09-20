import React from 'react';
import { Outlet } from 'react-router-dom';
import NavDock from './NavDock';
import TopStatusBar from './TopStatusBar';

export default function DashboardLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)', overflow: 'hidden' }}>
      <TopStatusBar />
      {/* full-width content; bottom padding keeps the last panel clear of the floating dock */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 96px', display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
        <Outlet />
      </main>
      <NavDock />
    </div>
  );
}
