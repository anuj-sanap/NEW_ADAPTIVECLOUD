// frontend/src/components/ui/StatTile.tsx
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface StatTileProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  className?: string;
}

export function StatTile({ label, value, subtext, icon, trend, className }: StatTileProps) {
  return (
    <div
      className={twMerge(
        clsx(
          'p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between transition-colors',
          className
        )
      )}
    >
      <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className="text-slate-400 dark:text-slate-500">{icon}</span>}
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{value}</div>
        {trend && (
          <span
            className={clsx(
              'text-xs font-medium',
              trend.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'
            )}
          >
            {trend.value}
          </span>
        )}
      </div>
      {subtext && <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{subtext}</div>}
    </div>
  );
}

