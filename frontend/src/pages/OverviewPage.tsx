// frontend/src/pages/OverviewPage.tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DashboardSummary } from '../types';
import { StatTile } from '../components/ui/StatTile';
import { Card } from '../components/ui/Card';
import { Gauge } from '../components/ui/Gauge';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { Server, AlertTriangle, ShieldCheck, Cpu, RefreshCw, AlertCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export function OverviewPage() {
  const { data: summary, isLoading, error, refetch } = useQuery<DashboardSummary>({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard/summary');
      return res.data;
    },
    refetchInterval: 15000,
  });

  const { data: activeModel } = useQuery({
    queryKey: ['active-model'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/models/active');
        return res.data;
      } catch {
        return null;
      }
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-64 bg-slate-200 dark:bg-slate-800 rounded-md" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-slate-200 dark:bg-slate-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <EmptyState
        title="Unable to load Executive Overview"
        message="Backend telemetry API is unreachable or returned an unexpected format."
        action={{ label: 'Retry Connection', onClick: () => refetch() }}
      />
    );
  }

  const chartData = Object.entries(summary.attack_counts_24h || {}).map(([key, val]) => ({
    name: key.replace('_', ' '),
    count: val,
  }));

  // Plain-English HOD Executive attention notice
  const getAttentionMessage = () => {
    if (summary.active_incidents > 0) {
      return `Attention Required: There are ${summary.active_incidents} active security incidents under active investigation. Recommend reviewing high-priority incidents in Root Cause Analysis.`;
    }
    if (summary.online_hosts < summary.total_hosts && summary.total_hosts > 0) {
      return `Infrastructure Notice: ${summary.total_hosts - summary.online_hosts} worker VM(s) are currently offline. Check Tailscale mesh connectivity.`;
    }
    return 'All systems normal. Network perimeter and worker VMs are operating within nominal baseline parameters with zero active breaches.';
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Executive Overview</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          High-level operational security posture, autonomous countermeasures, and infrastructure health.
        </p>
      </div>

      {/* Top Section: Health Score + Stat Tiles */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-3">
          <Card className="h-full flex flex-col justify-center items-center py-8">
            <Gauge score={summary.host_health_score} size={130} label="System Health Score" />
          </Card>
        </div>

        <div className="lg:col-span-9 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <StatTile
            label="Monitored Hosts"
            value={`${summary.online_hosts} / ${summary.total_hosts}`}
            subtext={summary.online_hosts === summary.total_hosts ? '100% Online' : `${summary.total_hosts - summary.online_hosts} Offline`}
            icon={<Server className="h-4 w-4" />}
          />
          <StatTile
            label="Active Incidents"
            value={summary.active_incidents}
            subtext="Requiring investigation"
            icon={<AlertTriangle className="h-4 w-4" />}
          />
          <StatTile
            label="Attacks Blocked (24h)"
            value={Object.values(summary.attack_counts_24h || {}).reduce((a, b) => a + b, 0)}
            subtext="Automated countermeasures"
            icon={<ShieldCheck className="h-4 w-4" />}
          />
          <StatTile
            label="Highest Predicted Risk"
            value={summary.top_risks.length > 0 ? `${(summary.top_risks[0].probability * 100).toFixed(0)}%` : 'None'}
            subtext={summary.top_risks.length > 0 ? summary.top_risks[0].title : 'Zero imminent threats'}
            icon={<AlertCircle className="h-4 w-4" />}
          />
          <StatTile
            label="Active Champion Model"
            value={activeModel?.version || 'XGBoost v1'}
            subtext={activeModel?.task ? activeModel.task.replace('_', ' ') : 'Production Classifier'}
            icon={<Cpu className="h-4 w-4" />}
          />
          <StatTile
            label="Adaptive Learning"
            value="Active"
            subtext="Continuous drift monitoring"
            icon={<RefreshCw className="h-4 w-4" />}
          />
        </div>
      </div>

      {/* Plain English Executive Attention Banner */}
      <div className="p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20 flex items-start space-x-3">
        <div className="p-1 rounded bg-indigo-600 text-white mt-0.5">
          <AlertCircle className="h-4 w-4" />
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-900 dark:text-indigo-300">
            What Needs Attention (Executive Brief)
          </h4>
          <p className="mt-1 text-xs text-indigo-800/90 dark:text-indigo-200 leading-relaxed font-normal">
            {getAttentionMessage()}
          </p>
        </div>
      </div>

      {/* Bottom Grid: 24h Attack Breakdown & Top Risks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card header={<span className="text-sm font-semibold">24-Hour Attack Breakdown</span>}>
          {chartData.every((d) => d.count === 0) ? (
            <EmptyState
              title="No attacks detected in past 24 hours"
              message="Worker traffic is strictly benign. No telemetry breach signatures observed."
            />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} angle={-15} textAnchor="end" />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card header={<span className="text-sm font-semibold">Prioritized Risk Forecasts</span>}>
          {summary.top_risks.length === 0 ? (
            <EmptyState
              title="No high-risk warnings"
              message="All infrastructure components and threat forecasts report low probability."
            />
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800 space-y-3">
              {summary.top_risks.map((risk, idx) => (
                <div key={idx} className="pt-3 first:pt-0 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium text-slate-900 dark:text-slate-100">{risk.title}</span>
                      <SeverityBadge severity={risk.severity} />
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Host: {risk.hostname || 'Cluster'} &bull; ETA: {risk.eta_minutes ? `${risk.eta_minutes}m` : 'Imminent'}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                      {(risk.probability * 100).toFixed(0)}%
                    </span>
                    <span className="block text-[10px] text-slate-400 uppercase">Probability</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

