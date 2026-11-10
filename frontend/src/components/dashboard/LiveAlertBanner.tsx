// frontend/src/components/dashboard/LiveAlertBanner.tsx
import type { AlertRecord } from '@/types'

const SEVERITY_STYLES: Record<string, string> = {
  low: 'bg-yellow-950 border-yellow-700 text-yellow-300',
  medium: 'bg-orange-950 border-orange-700 text-orange-300',
  high: 'bg-red-950 border-red-700 text-red-300',
  critical: 'bg-red-950 border-red-500 text-red-200 animate-pulse',
}

interface LiveAlertBannerProps {
  alerts: AlertRecord[]
}

export default function LiveAlertBanner({ alerts }: LiveAlertBannerProps) {
  const latest = alerts[0]
  if (!latest) return null

  const style = SEVERITY_STYLES[latest.severity] ?? SEVERITY_STYLES.medium

  return (
    <div className={`rounded-xl border px-5 py-4 ${style}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold uppercase text-xs tracking-widest">
            🚨 {latest.severity} alert
          </span>
          <span className="text-sm font-medium">{latest.message}</span>
        </div>
        <span className="text-xs opacity-60">
          +{alerts.length - 1} more
        </span>
      </div>
    </div>
  )
}
