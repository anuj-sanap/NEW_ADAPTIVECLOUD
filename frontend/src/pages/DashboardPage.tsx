// frontend/src/pages/DashboardPage.tsx
// Main dashboard: live metrics, predictions, and alerts via WebSocket.

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { AlertRecord, MetricRecord, PredictionRecord } from '@/types'
import MetricCard from '@/components/dashboard/MetricCard'
import LiveAlertBanner from '@/components/dashboard/LiveAlertBanner'
import MetricChart from '@/components/charts/MetricChart'
import AgentStatusBadge from '@/components/ui/AgentStatusBadge'

const MAX_HISTORY = 60  // Keep last 60 data points per chart

export default function DashboardPage() {
  const { username, role, logout } = useAuthStore()
  const { connected, subscribe } = useWebSocket()

  const [latestMetric, setLatestMetric] = useState<MetricRecord | null>(null)
  const [cpuHistory, setCpuHistory] = useState<{ ts: string; value: number }[]>([])
  const [memHistory, setMemHistory] = useState<{ ts: string; value: number }[]>([])
  const [latestPrediction, setLatestPrediction] = useState<PredictionRecord | null>(null)
  const [alerts, setAlerts] = useState<AlertRecord[]>([])

  // ── Subscribe to WebSocket channels ───────────────────────────────────────
  useEffect(() => {
    const unsubMetrics = subscribe<MetricRecord>('metrics', (env) => {
      setLatestMetric(env.data)
      setCpuHistory((prev) => [
        ...prev.slice(-MAX_HISTORY + 1),
        { ts: env.ts, value: env.data.cpu_percent },
      ])
      setMemHistory((prev) => [
        ...prev.slice(-MAX_HISTORY + 1),
        { ts: env.ts, value: env.data.memory_percent },
      ])
    })

    const unsubPredictions = subscribe<PredictionRecord>('predictions', (env) => {
      setLatestPrediction(env.data)
    })

    const unsubAlerts = subscribe<AlertRecord>('alerts', (env) => {
      setAlerts((prev) => [env.data, ...prev].slice(0, 50))
    })

    return () => {
      unsubMetrics()
      unsubPredictions()
      unsubAlerts()
    }
  }, [subscribe])

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Top nav ──────────────────────────────────────────────────────── */}
      <header className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight">🛡 AdaptiveCloud</span>
          <span className="text-xs text-gray-500">Security Monitor</span>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`}
            title={connected ? 'Connected' : 'Disconnected'}
          />
          <span className="text-sm text-gray-400">{username} · {role}</span>
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="p-6 space-y-6">
        {/* ── Live alerts ───────────────────────────────────────────────── */}
        {alerts.length > 0 && <LiveAlertBanner alerts={alerts} />}

        {/* ── Metric cards ──────────────────────────────────────────────── */}
        {latestMetric ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="CPU" value={`${latestMetric.cpu_percent.toFixed(1)}%`} />
            <MetricCard label="Memory" value={`${latestMetric.memory_percent.toFixed(1)}%`} />
            <MetricCard
              label="Net In"
              value={`${(latestMetric.net_bytes_recv_sec / 1024).toFixed(1)} KB/s`}
            />
            <MetricCard
              label="Connections"
              value={String(latestMetric.active_connections)}
            />
          </div>
        ) : (
          <div className="text-gray-500 text-sm">
            {connected ? 'Waiting for first metric from agents…' : 'WebSocket disconnected — reconnecting…'}
          </div>
        )}

        {/* ── Charts ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MetricChart title="CPU % (live)" data={cpuHistory} color="#3b82f6" unit="%" />
          <MetricChart title="Memory % (live)" data={memHistory} color="#10b981" unit="%" />
        </div>

        {/* ── Latest prediction ─────────────────────────────────────────── */}
        {latestPrediction && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <h2 className="text-sm font-semibold text-gray-400 mb-3">Latest ML Prediction</h2>
            <div className="flex items-center gap-4">
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  latestPrediction.label === 'benign'
                    ? 'bg-green-900 text-green-300'
                    : 'bg-red-900 text-red-300'
                }`}
              >
                {latestPrediction.label.replace(/_/g, ' ')}
              </span>
              <span className="text-gray-400 text-sm">
                Confidence: <span className="text-white font-mono">
                  {(latestPrediction.confidence * 100).toFixed(1)}%
                </span>
              </span>
              <span className="text-gray-600 text-xs ml-auto">
                Model: {latestPrediction.model_version}
              </span>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
