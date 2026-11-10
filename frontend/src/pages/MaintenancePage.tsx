// frontend/src/pages/MaintenancePage.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Wrench,
  HardDrive,
  Cpu,
  Database,
  Activity,
  Server,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import api from '@/api/client';
import { Host, HostMaintenanceDetail, MaintenanceForecast, Metric } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { format } from 'date-fns';

export default function MaintenancePage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [selectedHostId, setSelectedHostId] = useState<string>('');

  // 1. Fetch Hosts
  const { data: hosts = [], isLoading: hostsLoading } = useQuery<Host[]>({
    queryKey: ['hosts'],
    queryFn: async () => {
      const { data } = await api.get('/hosts');
      return data;
    },
  });

  const activeHostId = selectedHostId || (hosts.length > 0 ? hosts[0].id : '');

  // 2. Fetch Host Maintenance Detail
  const {
    data: detail,
    isLoading: detailLoading,
    refetch: refetchDetail,
  } = useQuery<HostMaintenanceDetail>({
    queryKey: ['maintenance', 'detail', activeHostId],
    queryFn: async () => {
      const { data } = await api.get(`/maintenance/hosts/${activeHostId}`);
      return data;
    },
    enabled: !!activeHostId,
  });

  // 3. Fetch Host Telemetry for trend charting
  const { data: metrics = [] } = useQuery<Metric[]>({
    queryKey: ['metrics', activeHostId, 'maintenance'],
    queryFn: async () => {
      const { data } = await api.get(`/hosts/${activeHostId}/metrics`, {
        params: { limit: 30 },
      });
      return data.reverse();
    },
    enabled: !!activeHostId,
    refetchInterval: 15000,
  });

  // 4. Fetch All Recent Maintenance Forecasts
  const { data: allForecasts = [], isLoading: forecastsLoading } = useQuery<MaintenanceForecast[]>({
    queryKey: ['maintenance', 'forecasts', activeHostId],
    queryFn: async () => {
      const params: Record<string, any> = { limit: 50 };
      if (activeHostId) params.host_id = activeHostId;
      const { data } = await api.get('/maintenance/forecasts', { params });
      return data;
    },
    enabled: !!activeHostId,
  });

  // 5. Trigger Maintenance Evaluation Mutation
  const evalMutation = useMutation({
    mutationFn: async (hostId: string) => {
      const { data } = await api.post(`/maintenance/evaluate/${hostId}`);
      return data;
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['maintenance'] });
      addToast({
        type: 'success',
        title: 'Maintenance Forecast Updated',
        message: `Evaluation completed for ${data.hostname || 'target host'}.`,
      });
    },
    onError: (err: any) => {
      addToast({
        type: 'error',
        title: 'Evaluation Failed',
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  const selectedHost = hosts.find((h) => h.id === activeHostId);

  // Transform metrics for Recharts
  const chartData = metrics.map((m) => ({
    time: format(new Date(m.ts), 'HH:mm'),
    cpu: Math.round(m.cpu),
    memory: Math.round(m.mem),
    disk: Math.round(m.disk),
  }));

  const diskEta = detail?.disk_fill_eta_days;
  const compStatus = detail?.component_status || {
    cpu: 'healthy',
    memory: 'healthy',
    disk: 'healthy',
    services: 'healthy',
  };

  const getStatusBadge = (st: string) => {
    if (st === 'critical') return <Badge variant="danger">Critical Risk</Badge>;
    if (st === 'warning') return <Badge variant="warning">Warning</Badge>;
    return <Badge variant="success">Normal</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <Wrench className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <span>Predictive Maintenance</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Forecasting hardware saturation, memory leaks, disk exhaustion, and service degradation before failure occurs.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <select
            value={activeHostId}
            onChange={(e) => setSelectedHostId(e.target.value)}
            disabled={hostsLoading || hosts.length === 0}
            className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {hosts.map((h) => (
              <option key={h.id} value={h.id}>
                {h.hostname} ({h.os_version || 'Windows'})
              </option>
            ))}
          </select>

          <button
            onClick={() => activeHostId && evalMutation.mutate(activeHostId)}
            disabled={evalMutation.isPending || !activeHostId}
            className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
          >
            {evalMutation.isPending ? (
              <RotateCcw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            <span>Run Predictive Health Check</span>
          </button>
        </div>
      </div>

      {/* Target Host Quick Details */}
      {selectedHost && (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="flex items-center space-x-3">
            <Server className="h-4 w-4 text-slate-400" />
            <span className="text-xs font-medium text-slate-500">Host Target:</span>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {selectedHost.hostname}
            </span>
            <Badge variant="outline">{selectedHost.os_version}</Badge>
            <Badge variant={selectedHost.status === 'online' ? 'success' : 'neutral'}>
              {selectedHost.status}
            </Badge>
          </div>
          <button
            onClick={() => refetchDetail()}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center space-x-1"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      )}

      {/* Component Risk Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Disk Exhaustion Card */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <HardDrive className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Disk Exhaustion</span>
            </div>
            {getStatusBadge(compStatus.disk)}
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {diskEta !== null && diskEta !== undefined ? `${diskEta.toFixed(1)} Days` : 'N/A'}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Theil-Sen linear fill projection</p>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-2">
            {diskEta !== null && diskEta !== undefined && diskEta < 7
              ? 'Warning: Volume running out of disk headroom rapidly.'
              : 'Storage consumption slope is within stable operating thresholds.'}
          </div>
        </Card>

        {/* CPU Saturation Card */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Cpu className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">CPU Saturation</span>
            </div>
            {getStatusBadge(compStatus.cpu)}
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {metrics.length > 0 ? `${Math.round(metrics[metrics.length - 1].cpu)}%` : '0%'}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Current compute load</p>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-2">
            Forecasting &gt;85% sustained spike in +15m horizon.
          </div>
        </Card>

        {/* Memory Leak Risk Card */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Memory Exhaustion</span>
            </div>
            {getStatusBadge(compStatus.memory)}
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {metrics.length > 0 ? `${Math.round(metrics[metrics.length - 1].mem)}%` : '0%'}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">RAM commit ratio</p>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-2">
            Detecting continuous heap accumulation in background processes.
          </div>
        </Card>

        {/* Monitored Services Card */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Service Reliability</span>
            </div>
            {getStatusBadge(compStatus.services)}
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {detail?.service_risks.length ?? 0} At Risk
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Crash &amp; restart risk</p>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-2">
            Monitoring Wazuh Agent, Windows Event Collector, TermService.
          </div>
        </Card>
      </div>

      {/* Historical Telemetry & Trend Projections */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Component Capacity Telemetry &amp; Saturation Thresholds
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Recent 30-sample trends for CPU, Memory, and Disk with 85% risk threshold.
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs font-medium">
            <span className="flex items-center space-x-1.5 text-indigo-600 dark:text-indigo-400">
              <span className="h-2 w-2 rounded-full bg-indigo-600 dark:bg-indigo-400" />
              <span>CPU %</span>
            </span>
            <span className="flex items-center space-x-1.5 text-amber-500">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <span>RAM %</span>
            </span>
            <span className="flex items-center space-x-1.5 text-emerald-500">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>Disk %</span>
            </span>
          </div>
        </div>

        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-xs text-slate-400">
            No telemetry data recorded yet for this host.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="mCpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="mMemGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
                <ReferenceLine y={85} stroke="#f43f5e" strokeDasharray="3 3" label={{ value: 'Risk Limit (85%)', fill: '#f43f5e', fontSize: 10 }} />
                <Area type="monotone" dataKey="cpu" stroke="#4f46e5" strokeWidth={2} fillOpacity={1} fill="url(#mCpuGrad)" name="CPU %" />
                <Area type="monotone" dataKey="memory" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#mMemGrad)" name="RAM %" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Maintenance Forecast Records Table */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Predictive Maintenance Diagnostic Records
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Logged component exhaustion projections and confidence ratings.
            </p>
          </div>
        </div>

        {forecastsLoading ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading maintenance records…</div>
        ) : allForecasts.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title="No Maintenance Forecasts Available"
            description="Run a predictive health check above or ensure the Windows agent is transmitting hardware metrics."
          />
        ) : (
          <DataTable
            data={allForecasts}
            searchPlaceholder="Filter component forecasts…"
            searchColumn="component"
            columns={[
              {
                header: 'Recorded At',
                accessor: 'created_at',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                    {format(new Date(row.created_at), 'yyyy-MM-dd HH:mm:ss')}
                  </span>
                ),
              },
              {
                header: 'Component',
                accessor: 'component',
                cell: (row) => (
                  <span className="font-semibold text-slate-900 dark:text-slate-100 uppercase text-xs font-mono">
                    {row.component}
                  </span>
                ),
              },
              {
                header: 'Metric Tracked',
                accessor: 'metric_name',
                cell: (row) => (
                  <Badge variant="outline">{row.metric_name}</Badge>
                ),
              },
              {
                header: 'Exhaustion Horizon',
                accessor: 'days_remaining',
                cell: (row) => {
                  const days = row.days_remaining;
                  const isUrgent = days < 3.0;
                  return (
                    <span
                      className={`font-mono text-xs font-bold ${
                        isUrgent ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {days > 0 ? `${days.toFixed(1)} days remaining` : '< 24 hours'}
                    </span>
                  );
                },
              },
              {
                header: 'Model Confidence',
                accessor: 'confidence',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                    {(row.confidence * 100).toFixed(0)}%
                  </span>
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}

