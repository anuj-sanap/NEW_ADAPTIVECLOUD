// frontend/src/components/dashboard/MetricCard.tsx
interface MetricCardProps {
  label: string
  value: string
  subtext?: string
}

export default function MetricCard({ label, value, subtext }: MetricCardProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-xs text-gray-500 uppercase tracking-widest">{label}</p>
      <p className="mt-2 text-3xl font-bold font-mono text-white">{value}</p>
      {subtext && <p className="mt-1 text-xs text-gray-500">{subtext}</p>}
    </div>
  )
}

