import React, { useState } from 'react';
import { LogEntry } from '../types/traffic';
import { List, ChevronUp, ChevronDown, Siren, Zap, AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface LogDrawerProps {
  logs: LogEntry[];
}

export const LogDrawer: React.FC<LogDrawerProps> = ({ logs }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-md">
      {/* Header Bar */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <List className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Real-Time Dispatch & System Telemetry Log
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
            {logs.length} events
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <span>{isOpen ? 'Collapse' : 'Expand'}</span>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      </button>

      {/* Log Entries View */}
      {isOpen && (
        <div className="p-4 border-t border-slate-800 max-h-60 overflow-y-auto flex flex-col gap-2 font-mono text-xs">
          {logs.length === 0 ? (
            <div className="text-slate-500 italic text-center py-4">No events logged yet.</div>
          ) : (
            logs.map((log) => {
              const icon =
                log.type === 'queue_jump' ? (
                  <Zap className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                ) : log.type === 'emergency' ? (
                  <Siren className="w-3.5 h-3.5 text-red-400 shrink-0 animate-pulse" />
                ) : log.type === 'hazard' ? (
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                ) : (
                  <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                );

              let textColor = 'text-slate-300';
              if (log.severity === 'emergency') textColor = 'text-red-300 font-semibold';
              if (log.severity === 'warning') textColor = 'text-amber-300';
              if (log.severity === 'success') textColor = 'text-emerald-300 font-semibold';

              return (
                <div
                  key={log.id}
                  className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-950/60 border border-slate-850"
                >
                  <span className="text-[10px] text-slate-500 shrink-0 pt-0.5">
                    [T+{String(log.tick).padStart(3, '0')}]
                  </span>
                  <div className="pt-0.5">{icon}</div>
                  <span className={`text-[11px] leading-tight ${textColor}`}>{log.message}</span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};
