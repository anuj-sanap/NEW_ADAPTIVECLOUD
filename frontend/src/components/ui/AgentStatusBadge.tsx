// frontend/src/components/ui/AgentStatusBadge.tsx
import type { AgentStatus } from '@/types'
import { clsx } from 'clsx'

interface Props {
  status: AgentStatus
}

export default function AgentStatusBadge({ status }: Props) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold',
        status === 'online'
          ? 'bg-green-900 text-green-300'
          : 'bg-gray-800 text-gray-500',
      )}
    >
      <span
        className={clsx(
          'w-1.5 h-1.5 rounded-full',
          status === 'online' ? 'bg-green-400' : 'bg-gray-600',
        )}
      />
      {status}
    </span>
  )
}

