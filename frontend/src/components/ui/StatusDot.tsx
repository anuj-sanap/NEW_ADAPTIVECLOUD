// frontend/src/components/ui/StatusDot.tsx
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type StatusType = 'online' | 'offline' | 'healthy' | 'warning' | 'critical' | 'pending';

interface StatusDotProps {
  status: StatusType | string;
  className?: string;
  pulse?: boolean;
}

export function StatusDot({ status, className, pulse = false }: StatusDotProps) {
  const norm = status.toLowerCase();

  let color = 'bg-slate-400';
  if (norm === 'online' || norm === 'healthy' || norm === 'verified') {
    color = 'bg-emerald-500';
  } else if (norm === 'warning' || norm === 'pending' || norm === 'investigating') {
    color = 'bg-amber-500';
  } else if (norm === 'critical' || norm === 'offline' || norm === 'failed') {
    color = 'bg-rose-500';
  }

  return (
    <span className="relative flex h-2.5 w-2.5">
      {pulse && (
        <span
          className={twMerge(
            clsx('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', color)
          )}
        />
      )}
      <span className={twMerge(clsx('relative inline-flex rounded-full h-2.5 w-2.5', color, className))} />
    </span>
  );
}

