// frontend/src/components/ui/EmptyState.tsx
import React from 'react';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title?: string;
  message?: string;
  description?: string;
  icon?: React.ReactNode | React.ComponentType<{ className?: string }>;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  title = 'No records found',
  message,
  description,
  icon,
  action,
}: EmptyStateProps) {
  const bodyText = description || message || 'There is currently no telemetry or data available for this section.';

  let renderedIcon = <Inbox className="h-6 w-6" />;
  if (icon) {
    if (React.isValidElement(icon)) {
      renderedIcon = icon;
    } else if (typeof icon === 'function' || typeof icon === 'object') {
      const IconComp = icon as React.ComponentType<{ className?: string }>;
      renderedIcon = <IconComp className="h-6 w-6" />;
    }
  }

  return (
    <div className="flex flex-col items-center justify-center p-10 text-center rounded-xl border border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 mb-3">
        {renderedIcon}
      </div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-sm">{bodyText}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
