// frontend/src/components/ui/Timeline.tsx
import React from 'react';
import { TimelineEvent } from '../../types';
import { format } from 'date-fns';
import { AlertCircle, Activity, ShieldAlert, Cpu } from 'lucide-react';

interface TimelineProps {
  events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps) {
  if (events.length === 0) {
    return <div className="text-xs text-slate-500 italic">No forensic events in this timeline.</div>;
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'security_event':
        return <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />;
      case 'metric_spike':
        return <Activity className="h-3.5 w-3.5 text-amber-500" />;
      case 'process':
        return <Cpu className="h-3.5 w-3.5 text-indigo-500" />;
      default:
        return <AlertCircle className="h-3.5 w-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
      {events.map((ev, idx) => {
        let formattedTime = ev.ts;
        try {
          formattedTime = format(new Date(ev.ts), 'HH:mm:ss (MMM d)');
        } catch {
          // ignore date parse issues
        }

        return (
          <div key={idx} className="relative group">
            <span className="absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm">
              {getEventIcon(ev.type)}
            </span>
            <div className="flex flex-col space-y-1">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono text-slate-400 dark:text-slate-500">{formattedTime}</span>
                <span className="text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                  {ev.source}
                </span>
              </div>
              <p className="text-xs text-slate-800 dark:text-slate-200 font-normal">{ev.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

