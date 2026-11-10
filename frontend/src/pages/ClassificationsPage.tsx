// frontend/src/pages/ClassificationsPage.tsx
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Classification } from '../types';
import { DataTable, Column } from '../components/ui/DataTable';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { useToast } from '../components/ui/Toast';
import { useAuthStore } from '../store/authStore';
import { Check, Edit3 } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { format } from 'date-fns';

const COLORS = ['#10b981', '#ef4444', '#f59e0b', '#6366f1', '#ec4899', '#8b5cf6'];

const LABELS = ['benign', 'brute_force', 'ddos', 'port_scan', 'unauthorized_access', 'suspicious_process'];

export function ClassificationsPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { isViewer } = useAuthStore();
  const [feedbackDialogId, setFeedbackDialogId] = useState<string | null>(null);
  const [selectedFixLabel, setSelectedFixLabel] = useState<string>('benign');

  const { data: classifications = [] } = useQuery<Classification[]>({
    queryKey: ['classifications'],
    queryFn: async () => {
      const res = await apiClient.get('/classifications?limit=100');
      return res.data;
    },
    refetchInterval: 10000,
  });

  const feedbackMutation = useMutation({
    mutationFn: async ({ detectionId, label, comments }: { detectionId?: string; label: string; comments?: string }) => {
      await apiClient.post('/learning/feedback', {
        detection_id: detectionId,
        true_label: label,
        comments: comments || 'Analyst verified via UI',
      });
    },
    onSuccess: () => {
      showToast('Human analyst feedback recorded for active learning.', 'success');
      setFeedbackDialogId(null);
      queryClient.invalidateQueries({ queryKey: ['classifications'] });
    },
    onError: (err: any) => {
      showToast(err.response?.data?.error?.message || 'Failed to submit feedback', 'error');
    },
  });

  // Calculate attack label distribution
  const distribution = React.useMemo(() => {
    const counts: Record<string, number> = {};
    classifications.forEach((c) => {
      counts[c.label] = (counts[c.label] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({
      name: name.replace('_', ' '),
      value,
    }));
  }, [classifications]);

  const columns: Column<Classification>[] = [
    {
      key: 'ts',
      header: 'Timestamp',
      render: (row) => <span className="font-mono text-xs">{format(new Date(row.ts), 'HH:mm:ss yyyy-MM-dd')}</span>,
    },
    {
      key: 'label',
      header: 'Predicted Class',
      render: (row) => (
        <Badge variant={row.label === 'benign' ? 'emerald' : 'rose'}>
          {row.label.toUpperCase().replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (row) => (
        <span className="font-mono text-xs font-semibold">
          {(row.confidence * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      key: 'model_id',
      header: 'Source',
      render: (row) => (
        <span className="text-xs text-slate-500 font-mono">
          {row.model_id ? 'Supervised XGBoost' : 'Rule Ingestion'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Analyst Feedback',
      sortable: false,
      render: (row) => {
        if (isViewer) {
          return <span className="text-xs text-slate-400 italic">Read-only</span>;
        }

        return (
          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => feedbackMutation.mutate({ label: row.label, comments: 'Confirmed correct by analyst' })}
              title="Confirm classification is accurate"
              className="p-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-slate-600 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setFeedbackDialogId(row.id)}
              title="Reclassify or fix mislabeled flow"
              className="p-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-slate-600 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            >
              <Edit3 className="h-3.5 w-3.5" />
            </button>

            {feedbackDialogId === row.id && (
              <div className="flex items-center space-x-1">
                <select
                  value={selectedFixLabel}
                  onChange={(e) => setSelectedFixLabel(e.target.value)}
                  className="text-xs py-0.5 px-1.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                >
                  {LABELS.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => feedbackMutation.mutate({ label: selectedFixLabel, comments: 'Analyst corrected misclassification' })}
                  className="px-2 py-0.5 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700 font-medium"
                >
                  Save
                </button>
              </div>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Attack Classification & Feedback</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Multiclass supervised classification across canonical flow features with integrated human-in-the-loop feedback.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card header={<span className="text-sm font-semibold">Classification Distribution</span>} className="h-full">
            {distribution.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-xs text-slate-400">
                No classification records available.
              </div>
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={distribution} innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                      {distribution.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '0.75rem', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2">
          <DataTable
            columns={columns}
            data={classifications}
            searchKey="label"
            searchPlaceholder="Filter by attack label..."
            emptyTitle="No classification events recorded"
            emptyMessage="Flow feature classifier has not received any classified network flows."
          />
        </div>
      </div>
    </div>
  );
}

