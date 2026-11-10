// frontend/src/components/ui/Gauge.tsx
import React from 'react';

interface GaugeProps {
  score: number; // 0 to 100
  size?: number;
  label?: string;
}

export function Gauge({ score, size = 120, label = 'Health Score' }: GaugeProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  let color = '#10b981'; // emerald
  if (normalizedScore < 50) {
    color = '#f43f5e'; // rose
  } else if (normalizedScore < 80) {
    color = '#f59e0b'; // amber
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-100 dark:text-slate-800"
            fill="transparent"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{Math.round(score)}</span>
          <span className="text-[10px] uppercase font-semibold text-slate-400">/ 100</span>
        </div>
      </div>
      {label && <span className="mt-2 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>}
    </div>
  );
}

