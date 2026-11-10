// frontend/src/pages/DetectionsPage.tsx
import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Detection } from '../types';
import { DataTable, Column } from '../components/ui/DataTable';
import { Badge } from '../components/ui/Badge';
import { Drawer } from '../components/ui/Drawer';
import { useLiveChannel } from '../hooks/useLiveChannel';
import { format } from 'date-fns';

export function DetectionsPage() {
  const queryClient = useQueryClient();
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);
  const [filterAttackOnly, setFilterAttackOnly] = useState<boolean>(false);

  // Subscribe to live detections channel
  useLiveChannel('detections', () => {
    queryClient.invalidateQueries({ queryKey: ['detections'] });
  });

  const { data: detections = [], isLoading } = useQuery<Detection[]>({
    queryKey: ['detections', filterAttackOnly],
    queryFn: async () => {
      const url = filterAttackOnly ? '/detections?is_attack=true&limit=100' : '/detections?limit=100';
      const res = await apiClient.get(url);
      return res.data;
    },
    refetchInterval: 10000,
  });

  const columns: Column<Detection>[] = [
    {
      key: 'ts',
      header: 'Timestamp',
      render: (row) => <span className="font-mono text-xs">{format(new Date(row.ts), 'HH:mm:ss yyyy-MM-dd')}</span>,
    },
    {
      key: 'is_attack',
      header: 'Verdict',
      render: (row) => (
        <Badge variant={row.is_attack ? 'rose' : 'emerald'}>
          {row.is_attack ? 'ANOMALOUS / ATTACK' : 'BENIGN'}
        </Badge>
      ),
    },
    {
      key: 'anomaly_score',
      header: 'Anomaly Score',
      render: (row) => (
        <span className={`font-mono text-xs font-semibold ${row.anomaly_score > 0.6 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-600 dark:text-slate-400'}`}>
          {row.anomaly_score.toFixed(4)}
        </span>
      ),
    },
    {
      key: 'host_id',
      header: 'Host UUID',
      render: (row) => <span className="font-mono text-xs text-slate-500 truncate max-w-[120px] block">{row.host_id}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge variant="outline">{row.status.toUpperCase()}</Badge>,
    },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Attack Detection Feed</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time telemetry stream evaluated by unsupervised Isolation Forest anomaly detectors.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setFilterAttackOnly(!filterAttackOnly)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              filterAttackOnly
                ? 'bg-rose-50 border-rose-300 text-rose-700 dark:bg-rose-950/60 dark:border-rose-800 dark:text-rose-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            {filterAttackOnly ? 'Showing Attacks Only' : 'Show All Telemetry'}
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={detections}
        searchKey="host_id"
        searchPlaceholder="Filter by Host ID..."
        emptyTitle="No anomaly detections recorded"
        emptyMessage="Isolation Forest sensors have not flagged any anomalous flow windows."
        onRowClick={(row) => setSelectedDetection(row)}
      />

      {/* Detection Detail Drawer */}
      <Drawer
        isOpen={!!selectedDetection}
        onClose={() => setSelectedDetection(null)}
        title="Anomaly Detection Forensics"
        subtitle={selectedDetection ? `ID: ${selectedDetection.id}` : ''}
      >
        {selectedDetection && (
          <div className="space-y-6 text-xs">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Verdict:</span>
                <Badge variant={selectedDetection.is_attack ? 'rose' : 'emerald'}>
                  {selectedDetection.is_attack ? 'ATTACK DETECTED' : 'BENIGN'}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Anomaly Score:</span>
                <span className="font-mono font-semibold">{selectedDetection.anomaly_score.toFixed(6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Timestamp:</span>
                <span className="font-mono">{format(new Date(selectedDetection.ts), 'yyyy-MM-dd HH:mm:ss UTC')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Host ID:</span>
                <span className="font-mono">{selectedDetection.host_id}</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Flow Features & Telemetry Diagnostics
              </h4>
              <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-900 text-slate-100 p-3 font-mono text-[11px] overflow-x-auto max-h-96 scrollbar-thin">
                <pre>{JSON.stringify(selectedDetection.details || {}, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

