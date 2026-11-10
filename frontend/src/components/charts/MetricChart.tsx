// frontend/src/components/charts/MetricChart.tsx
// Recharts line chart for time-series metric data.

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

interface DataPoint {
  ts: string
  value: number
}

interface MetricChartProps {
  title: string
  data: DataPoint[]
  color: string
  unit: string
  domain?: [number, number]
}

export default function MetricChart({
  title,
  data,
  color,
  unit,
  domain = [0, 100],
}: MetricChartProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-400 mb-4">{title}</h3>
      {data.length === 0 ? (
        <div className="h-40 flex items-center justify-center text-gray-600 text-sm">
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="ts"
              tickFormatter={(v: string) => format(new Date(v), 'HH:mm:ss')}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={domain}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              tickFormatter={(v: number) => `${v}${unit}`}
            />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#9ca3af', fontSize: 11 }}
              formatter={(v: number) => [`${v.toFixed(1)}${unit}`, title]}
              labelFormatter={(label: string) => format(new Date(label), 'HH:mm:ss')}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
