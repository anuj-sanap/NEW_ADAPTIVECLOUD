// frontend/src/components/layout/TopBar.tsx
import React from 'react';
import { Sun, Moon, LogOut, Shield } from 'lucide-react';
import { useThemeStore } from '../../store/themeStore';
import { useAuthStore } from '../../store/authStore';
import { useLiveChannel } from '../../hooks/useLiveChannel';
import { StatusDot } from '../ui/StatusDot';
import { Badge } from '../ui/Badge';

export function TopBar() {
  const { isDark, toggleTheme } = useThemeStore();
  const { user, logout } = useAuthStore();
  const { status: wsStatus } = useLiveChannel('live');

  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between z-10 transition-colors">
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-xs text-slate-600 dark:text-slate-300">
          <StatusDot status={wsStatus === 'connected' ? 'online' : wsStatus === 'connecting' ? 'pending' : 'offline'} pulse={wsStatus === 'connected'} />
          <span className="capitalize font-mono text-[11px]">{wsStatus === 'connected' ? 'Live Stream Active' : wsStatus}</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Dark/Light mode toggle */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* User profile & Role badge */}
        {user && (
          <div className="flex items-center space-x-3 pl-4 border-l border-slate-200 dark:border-slate-800">
            <div className="flex flex-col text-right">
              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">{user.username}</span>
              <div className="flex justify-end">
                <Badge variant={user.role === 'admin' ? 'indigo' : user.role === 'analyst' ? 'amber' : 'neutral'} className="text-[10px] py-0 px-1.5">
                  <Shield className="h-2.5 w-2.5 mr-1" />
                  {user.role.toUpperCase()}
                </Badge>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

