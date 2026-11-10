// frontend/src/components/layout/Sidebar.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  ShieldAlert,
  Cpu,
  Search,
  TrendingUp,
  Wrench,
  ShieldCheck,
  BrainCircuit,
  FileSpreadsheet,
  Cloud,
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Executive Overview', path: '/', icon: LayoutDashboard },
  { name: 'Live Cloud Monitoring', path: '/monitoring', icon: Activity },
  { name: 'Attack Detection', path: '/detections', icon: ShieldAlert },
  { name: 'Attack Classification', path: '/classifications', icon: Cpu },
  { name: 'Root Cause Analysis', path: '/rca', icon: Search },
  { name: 'Threat Prediction', path: '/predictions', icon: TrendingUp },
  { name: 'Predictive Maintenance', path: '/maintenance', icon: Wrench },
  { name: 'Response & Recovery', path: '/responses', icon: ShieldCheck },
  { name: 'ML & Adaptive Learning', path: '/learning', icon: BrainCircuit },
  { name: 'Reports & Audit Logs', path: '/reports', icon: FileSpreadsheet },
];

export function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-screen select-none transition-colors">
      <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-800 space-x-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
          <Cloud className="h-5 w-5" />
        </div>
        <div>
          <span className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">AdaptiveCloud</span>
          <span className="block text-[10px] text-slate-400 font-mono tracking-wider uppercase">Zero-Trust SecOps</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                }`
              }
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="truncate">{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400 text-center">
        v1.0.0 &bull; INR 0 Budget Compliant
      </div>
    </aside>
  );
}

