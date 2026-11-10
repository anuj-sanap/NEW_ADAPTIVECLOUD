// frontend/src/pages/RcaPage.tsx
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Incident, RCAReport } from '../types';
import { DataTable, Column } from '../components/ui/DataTable';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Timeline } from '../components/ui/Timeline';
import { Drawer } from '../components/ui/Drawer';
import { EmptyState } from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import { useAuthStore } from '../store/authStore';
import { RefreshCw, FileText, Globe, Terminal, ShieldAlert } from 'lucide-react';
import { format } from 'date-fns';

export function RcaPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { isViewer } = useAuthStore();
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  // Fetch incidents
  const { data: incidents = [] } = useQuery<Incident[]>({
    queryKey: ['incidents'],
    queryFn: async () => {
      const res = await apiClient.get('/incidents?limit=50');
      return res.data;
    },
    refetchInterval: 10000,
  });

  // Fetch RCA report for selected incident
  const { data: rcaReport, isLoading: rcaLoading } = useQuery<RCAReport>({
    queryKey: ['rca-report', selectedIncident?.id],
    queryFn: async () => {
      if (!selectedIncident?.id) return null;
      const res = await apiClient.get(`/rca/${selectedIncident.id}`);
      return res.data;
    },
    enabled: !!selectedIncident?.id,
  });

  const regenerateMutation = useMutation({
    mutationFn: async (incidentId: string) => {
      const res = await apiClient.post(`/rca/${incidentId}/regenerate`);
      return res.data;
    },
    onSuccess: () => {
      showToast('RCA forensics synthesized with latest telemetry.', 'success');
      queryClient.invalidateQueries({ queryKey: ['rca-report', selectedIncident?.id] });
    },
  });

  const columns: Column<Incident>[] = [
    {
      key: 'created_at',
      header: 'Detected',
      render: (row) => <span className="font-mono text-xs">{format(new Date(row.created_at), 'HH:mm:ss yyyy-MM-dd')}</span>,
    },
    {
      key: 'title',
      header: 'Incident Title',
      render: (row) => (
        <span className="font-medium text-xs text-slate-900 dark:text-slate-100 hover:text-indigo-600 transition-colors">
          {row.title}
        </span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (row) => <SeverityBadge severity={row.severity} />,
    },
    {
      key: 'status',
      header: 'Investigation Status',
      render: (row) => <Badge variant="outline">{row.status.toUpperCase()}</Badge>,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Root Cause Analysis (RCA)</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Automated forensic correlation across Windows security events, flow telemetry, and metric spikes.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={incidents}
        searchKey="title"
        searchPlaceholder="Filter incidents..."
        emptyTitle="No security incidents logged"
        emptyMessage="Security sensors report no correlated attack incidents requiring forensic RCA."
        onRowClick={(row) => setSelectedIncident(row)}
      />

      {/* Forensic RCA Drawer */}
      <Drawer
        isOpen={!!selectedIncident}
        onClose={() => setSelectedIncident(null)}
        title="Forensic Root Cause Analysis"
        subtitle={selectedIncident ? selectedIncident.title : ''}
      >
        {rcaLoading ? (
          <div className="space-y-4 animate-pulse">
            <div className="h-6 w-3/4 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-24 bg-slate-200 dark:bg-slate-800 rounded-xl" />
            <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl" />
          </div>
        ) : rcaReport ? (
          <div className="space-y-6 text-xs">
            {/* Header Controls */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center space-x-2">
                <SeverityBadge severity={selectedIncident?.severity || 'high'} />
                <Badge variant="indigo">Confidence: {(rcaReport.confidence * 100).toFixed(0)}%</Badge>
              </div>
              {!isViewer && (
                <button
                  onClick={() => regenerateMutation.mutate(selectedIncident!.id)}
                  disabled={regenerateMutation.isPending}
                  className="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${regenerateMutation.isPending ? 'animate-spin' : ''}`} />
                  <span>Re-analyze</span>
                </button>
              )}
            </div>

            {/* Plain English HOD Executive Summary */}
            <div className="p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-indigo-950/20">
              <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-900 dark:text-indigo-300">
                Plain-English Summary (For Leadership)
              </span>
              <p className="mt-1 text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-normal">
                {rcaReport.plain_english_summary}
              </p>
            </div>

            {/* Probable Cause Template */}
            <Card header={<span className="text-xs font-semibold">Probable Cause</span>}>
              <div className="flex items-start space-x-2 text-rose-700 dark:text-rose-400">
                <ShieldAlert className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p className="font-medium text-xs">{rcaReport.probable_cause}</p>
              </div>
            </Card>

            {/* Source IPs & Affected Hosts */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <span className="text-[10px] uppercase font-medium text-slate-400 flex items-center">
                  <Globe className="h-3 w-3 mr-1" /> Source IPs
                </span>
                <div className="mt-2 space-y-1 font-mono">
                  {rcaReport.source_ips.map((s, idx) => (
                    <div key={idx} className="flex justify-between items-center text-[11px]">
                      <span>{s.ip}</span>
                      <Badge variant="neutral" className="text-[10px]">{s.country || 'Unknown'}</Badge>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <span className="text-[10px] uppercase font-medium text-slate-400">Affected Hosts</span>
                <div className="mt-2 space-y-1 font-mono text-[11px] text-slate-800 dark:text-slate-200">
                  {rcaReport.affected_hosts.map((h, idx) => (
                    <div key={idx}>{h}</div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recommended Windows Actions */}
            <Card header={<span className="text-xs font-semibold">Recommended Remediation (PowerShell)</span>}>
              <div className="space-y-2">
                {rcaReport.recommended_actions.map((act, idx) => (
                  <div key={idx} className="p-2 rounded bg-slate-900 text-slate-100 font-mono text-[11px] flex items-center justify-between">
                    <span className="truncate">{act}</span>
                    <Terminal className="h-3.5 w-3.5 text-slate-400 flex-shrink-0 ml-2" />
                  </div>
                ))}
              </div>
            </Card>

            {/* Chronological Forensic Timeline */}
            <Card header={<span className="text-xs font-semibold">Forensic Telemetry Timeline</span>}>
              <Timeline events={rcaReport.timeline} />
            </Card>
          </div>
        ) : (
          <EmptyState title="RCA Report Not Available" message="Forensic data could not be generated for this incident." />
        )}
      </Drawer>
    </div>
  );
}

