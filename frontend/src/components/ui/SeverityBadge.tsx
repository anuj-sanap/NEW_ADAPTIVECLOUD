// frontend/src/components/ui/SeverityBadge.tsx
import React from 'react';
import { Badge, BadgeVariant } from './Badge';

interface SeverityBadgeProps {
  severity: string;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const norm = severity.toLowerCase();

  let variant: BadgeVariant = 'neutral';
  if (norm === 'critical' || norm === 'high') {
    variant = 'rose';
  } else if (norm === 'medium' || norm === 'warning') {
    variant = 'amber';
  } else if (norm === 'low' || norm === 'info') {
    variant = 'indigo';
  } else if (norm === 'healthy' || norm === 'resolved') {
    variant = 'emerald';
  }

  return (
    <Badge variant={variant} className={className}>
      {severity.toUpperCase()}
    </Badge>
  );
}

