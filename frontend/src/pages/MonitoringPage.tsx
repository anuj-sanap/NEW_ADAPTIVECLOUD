// frontend/src/pages/MonitoringPage.tsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Host, Metric } from '../types';
import { Card } from '../components/ui/Card';
import { StatusDot } from '../components/ui/StatusDot';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Server, Activity, ShieldCheck, HardDrive, Cpu } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

export function MonitoringPage() {
  const [selectedHostId, setSelectedHostId] = useState<string | null>(null);

  // Fetch hosts
  const { data: hosts = [], isLoading: hostsLoading } = useQuery<Host[]>({
    queryKey: ['hosts'],
    queryFn: async () => {
      const res = await apiClient.get('/hosts');
      return res.data;
    },
    refetchInterval: 10000,
  });

  const activeHost = selectedHostId ? hosts.find((h) => h.id === selectedHostId) : hosts[0];

  // Fetch historical metrics for active host
  const { data: metricsData } = useQuery<{ host_id: string; points: Metric[] }>({
    queryKey: ['host-metrics', activeHost?.id],
    queryFn: async () => {
      if (!activeHost?.id) return { host_id: '', points: [] };
      const res = await apiClient.get(`/hosts/${activeHost.id}/metrics?limit=30`);
      return res.data;
    },
    enabled: !!activeHost?.id,
    refetchInterval: 5000,
  });

  const metrics = metricsData?.points || [];
  const latestMetric = metrics[metrics.length - 1];

  const chartSeries = metrics.map((m) => ({
    time: format(new Date(m.ts), 'HH:mm:ss'),
    cpu: m.cpu,
    memory: m.mem,
    disk: m.disk,
    conn: m.conn_count,
  }));

  if (hostsLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-64 bg-slate-200 dark:bg-slate-800 rounded-md" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (hosts.length === 0) {
    return (
      <EmptyState
        title="No Monitored Hosts Found"
        message="No Windows or Linux cloud workers are registered with the control stack. Run bootstrap_worker.ps1 on your VM."
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Live Cloud Monitoring</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Real-time resource utilization, active network sockets, and Windows service status across infrastructure.
        </p>
      </div>

      {/* Host selection cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {hosts.map((host) => {
          const isSelected = (activeHost?.id || hosts[0].id) === host.id;
          return (
            <div
              key={host.id}
              onClick={() => setSelectedHostId(host.id)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/20 dark:bg-indigo-950/20'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Server className="h-4 w-4 text-slate-500" />
                  <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">{host.hostname}</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <StatusDot status={host.status} pulse={host.status === 'online'} />
                  <span className="text-[11px] uppercase font-mono text-slate-500">{host.status}</span>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>{host.ip_address || 'No IP'}</span>
                <span>{host.agent_platform}</span>
              </div>
            </div>
          );
        })}
      </div>

      {activeHost && (
        <>
          {/* Quick Stats for Selected Host */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <span className="text-[10px] uppercase font-medium text-slate-400">CPU Load</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xl font-bold text-slate-900 dark:text-slate-100">{latestMetric?.cpu ?? 0}%</span>
                <Cpu className="h-4 w-4 text-indigo-500" />
              </div>
            </div>
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <span className="text-[10px] uppercase font-medium text-slate-400">RAM Usage</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xl font-bold text-slate-900 dark:text-slate-100">{latestMetric?.mem ?? 0}%</span>
                <Activity className="h-4 w-4 text-emerald-500" />
              </div>
            </div>
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <span className="text-[10px] uppercase font-medium text-slate-400">Disk Used</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xl font-bold text-slate-900 dark:text-slate-100">{latestMetric?.disk ?? 0}%</span>
                <HardDrive className="h-4 w-4 text-amber-500" />
              </div>
            </div>
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <span className="text-[10px] uppercase font-medium text-slate-400">Active Sockets</span>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xl font-bold text-slate-900 dark:text-slate-100">{latestMetric?.conn_count ?? 0}</span>
                <ShieldCheck className="h-4 w-4 text-slate-400" />
              </div>
            </div>
          </div>

          {/* Real-time Utilization Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card header={<span className="text-sm font-semibold">Live CPU & Memory Utilization</span>}>
              {chartSeries.length === 0 ? (
                <EmptyState title="Waiting for telemetry samples" message="Agent is spooling initial metrics." />
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} />
                      <YAxis stroke="#94a3b8" fontSize={10} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '0.75rem', fontSize: '11px' }} />
                      <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} />
                      <Area type="monotone" dataKey="memory" name="RAM %" stroke="#10b981" fill="#10b981" fillOpacity={0.15} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            <Card header={<span className="text-sm font-semibold">Disk & Socket Activity</span>}>
              {chartSeries.length === 0 ? (
                <EmptyState title="Waiting for telemetry samples" message="Agent is spooling initial metrics." />
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} />
                      <YAxis stroke="#94a3b8" fontSize={10} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '0.75rem', fontSize: '11px' }} />
                      <Area type="monotone" dataKey="disk" name="Disk %" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} />
                      <Area type="monotone" dataKey="conn" name="TCP Connections" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.1} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>

          {/* Processes & Services Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card header={<span className="text-sm font-semibold">Top Resource Processes</span>}>
              {(!latestMetric?.extra?.top_cpu_processes || latestMetric.extra.top_cpu_processes.length === 0) ? (
                <EmptyState title="No process telemetry" message="Process auditing telemetry not received in latest sample." />
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {latestMetric.extra.top_cpu_processes.slice(0, 5).map((p, i) => (
                    <div key={i} className="py-2 flex items-center justify-between">
                      <span className="font-mono text-slate-800 dark:text-slate-200">{p.name} (PID: {p.pid})</span>
                      <Badge variant="indigo">{p.cpu_percent}% CPU</Badge>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card header={<span className="text-sm font-semibold">Monitored System Services</span>}>
              {(!latestMetric?.extra?.services || Object.keys(latestMetric.extra.services).length === 0) ? (
                <EmptyState title="No services tracked" message="No Windows services reported in latest telemetry." />
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {Object.entries(latestMetric.extra.services).map(([svc, status], i) => (
                    <div key={i} className="py-2 flex items-center justify-between">
                      <span className="font-medium text-slate-800 dark:text-slate-200">{svc}</span>
                      <Badge variant={status === 'running' ? 'emerald' : 'rose'}>{status.toUpperCase()}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

