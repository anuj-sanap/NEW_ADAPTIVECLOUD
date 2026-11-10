// frontend/src/pages/ReportsAuditPage.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileSpreadsheet,
  Download,
  Shield,
  FileText,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import api from '@/api/client';
import { AuditLog, ReportSummary } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { format } from 'date-fns';

export default function ReportsAuditPage() {
  const { addToast } = useToast();
  const [reportDays, setReportDays] = useState<number>(7);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  // 1. Fetch Executive Report Summary
  const {
    data: summary,
    isLoading: summaryLoading,
    refetch: refetchSummary,
  } = useQuery<ReportSummary>({
    queryKey: ['reports', 'summary', reportDays],
    queryFn: async () => {
      const { data } = await api.get('/reports/summary', {
        params: { days: reportDays },
      });
      return data;
    },
  });

  // 2. Fetch System Audit Logs
  const {
    data: auditLogs = [],
    isLoading: auditLoading,
    refetch: refetchAudit,
  } = useQuery<AuditLog[]>({
    queryKey: ['audit'],
    queryFn: async () => {
      const { data } = await api.get('/audit', {
        params: { limit: 100 },
      });
      return data;
    },
    refetchInterval: 15000,
  });

  // Export File Download Handler
  const handleExport = async (formatType: 'csv' | 'json') => {
    setDownloadingFormat(formatType);
    try {
      const res = await api.get('/reports/export', {
        params: { format: formatType, days: reportDays },
        responseType: 'blob',
      });

      const blob = new Blob([res.data], {
        type: formatType === 'csv' ? 'text/csv' : 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `adaptivecloud_report_${reportDays}d_${Date.now()}.${formatType}`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      addToast({
        type: 'success',
        title: 'Report Downloaded',
        message: `Saved ${formatType.toUpperCase()} report for ${reportDays} days window.`,
      });
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Export Failed',
        message: err.response?.data?.detail || err.message,
      });
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <FileSpreadsheet className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <span>Reports &amp; Audit Logs</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Generate compliance summaries, export forensic telemetry reports (CSV/JSON), and audit system modifications.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={reportDays}
            onChange={(e) => setReportDays(Number(e.target.value))}
            className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
          </select>

          <button
            onClick={() => {
              refetchSummary();
              refetchAudit();
            }}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Executive Compliance & Security Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="p-4 space-y-1">
          <span className="text-xs font-medium text-slate-500">System Uptime</span>
          <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
            {summary?.uptime_percentage !== undefined ? `${summary.uptime_percentage.toFixed(1)}%` : '—'}
          </div>
          <p className="text-[11px] text-slate-400">Target SLA: 99.5%</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-xs font-medium text-slate-500">Active / Total Hosts</span>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {summary ? `${summary.online_hosts} / ${summary.total_hosts}` : '—'}
          </div>
          <p className="text-[11px] text-slate-400">Monitored Cloud Workers</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-xs font-medium text-slate-500">Security Detections</span>
          <div className="text-2xl font-bold font-mono text-indigo-600 dark:text-indigo-400">
            {summary?.total_detections ?? 0}
          </div>
          <p className="text-[11px] text-slate-400">In {reportDays}-day period</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-xs font-medium text-slate-500">Total Incidents</span>
          <div className="text-2xl font-bold font-mono text-amber-600 dark:text-amber-400">
            {summary?.total_incidents ?? 0}
          </div>
          <p className="text-[11px] text-slate-400">Correlated security events</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-xs font-medium text-slate-500">Attacks Blocked</span>
          <div className="text-2xl font-bold font-mono text-rose-600 dark:text-rose-400">
            {summary?.attacks_blocked ?? 0}
          </div>
          <p className="text-[11px] text-slate-400">Enforced firewall drops</p>
        </Card>
      </div>

      {/* Export Action Card */}
      <Card className="p-5 bg-gradient-to-r from-indigo-50/50 via-white to-slate-50 dark:from-indigo-950/20 dark:via-slate-900 dark:to-slate-900">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Download className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Forensic Telemetry &amp; Incident Export Center
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Export complete audit logs, incident histories, and attack signatures for HOD compliance reviews.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => handleExport('csv')}
              disabled={!!downloadingFormat}
              className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              <span>{downloadingFormat === 'csv' ? 'Exporting…' : 'Export CSV Report'}</span>
            </button>

            <button
              onClick={() => handleExport('json')}
              disabled={!!downloadingFormat}
              className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-50 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors border border-slate-300 dark:border-slate-700"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>{downloadingFormat === 'json' ? 'Exporting…' : 'Export JSON'}</span>
            </button>
          </div>
        </div>
      </Card>

      {/* System Audit Log Table */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              System &amp; Administrative Audit Logs
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Immutable audit trail recording administrative actions, promotions, policy edits, and responses.
            </p>
          </div>
        </div>

        {auditLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading audit log entries…</div>
        ) : auditLogs.length === 0 ? (
          <EmptyState
            icon={Shield}
            title="Zero Audit Log Entries Recorded"
            description="System and administrative activity will be logged here automatically as actions occur."
          />
        ) : (
          <DataTable
            data={auditLogs}
            searchPlaceholder="Filter by action or resource…"
            searchColumn="action"
            columns={[
              {
                header: 'Timestamp',
                accessor: 'created_at',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                    {format(new Date(row.created_at), 'yyyy-MM-dd HH:mm:ss')}
                  </span>
                ),
              },
              {
                header: 'Action',
                accessor: 'action',
                cell: (row) => (
                  <Badge variant="indigo">{row.action}</Badge>
                ),
              },
              {
                header: 'Resource Type',
                accessor: 'resource_type',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-300 font-medium">
                    {row.resource_type}
                  </span>
                ),
              },
              {
                header: 'Resource ID / Target',
                accessor: 'resource_id',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-500">
                    {row.resource_id ? row.resource_id.slice(0, 18) : '—'}
                  </span>
                ),
              },
              {
                header: 'Origin IP / User',
                accessor: 'ip_address',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-500">
                    {row.ip_address || (row.user_id ? `User:${row.user_id.slice(0, 8)}` : 'System')}
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

