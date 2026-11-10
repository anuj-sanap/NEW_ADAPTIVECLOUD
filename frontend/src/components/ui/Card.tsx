// frontend/src/components/ui/Card.tsx
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export function Card({ children, className, header, footer, ...props }: CardProps) {
  return (
    <div
      className={twMerge(
        clsx(
          'rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden transition-colors',
          className
        )
      )}
      {...props}
    >
      {header && <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800/80 font-medium">{header}</div>}
      <div className="p-6">{children}</div>
      {footer && <div className="px-6 py-3 border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/50 text-sm">{footer}</div>}
    </div>
  );
}

