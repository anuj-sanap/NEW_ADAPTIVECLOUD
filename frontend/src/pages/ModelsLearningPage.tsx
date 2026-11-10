// frontend/src/pages/ModelsLearningPage.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BrainCircuit,
  Award,
  Zap,
  Activity,
  RotateCcw,
  Play,
  Check,
  X,
  AlertTriangle,
  GitCompare,
  Sliders,
} from 'lucide-react';
import api from '@/api/client';
import { DriftEvent, MLModel, RetrainingJob } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useToast } from '@/components/ui/Toast';
import { useAuthStore } from '@/store/authStore';
import { format } from 'date-fns';

export default function ModelsLearningPage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const isViewer = useAuthStore((s) => s.isViewer);

  // Retrain modal state
  const [showRetrainModal, setShowRetrainModal] = useState(false);
  const [forceRetrain, setForceRetrain] = useState(false);
  const [replayRatio, setReplayRatio] = useState(0.2);

  // Confirm dialog state
  const [confirmState, setConfirmState] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    description: '',
    onConfirm: () => {},
  });

  // 1. Fetch Registered Models
  const {
    data: models = [],
    isLoading: modelsLoading,
    refetch: refetchModels,
  } = useQuery<MLModel[]>({
    queryKey: ['models'],
    queryFn: async () => {
      const { data } = await api.get('/models');
      return data;
    },
  });

  // 2. Fetch Retraining Jobs
  const {
    data: jobs = [],
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery<RetrainingJob[]>({
    queryKey: ['learning', 'jobs'],
    queryFn: async () => {
      const { data } = await api.get('/learning/jobs');
      return data;
    },
    refetchInterval: 10000,
  });

  // 3. Fetch Drift Events
  const {
    data: driftEvents = [],
    isLoading: driftLoading,
    refetch: refetchDrift,
  } = useQuery<DriftEvent[]>({
    queryKey: ['learning', 'drift'],
    queryFn: async () => {
      const { data } = await api.get('/learning/drift');
      return data;
    },
    refetchInterval: 15000,
  });

  // Trigger Retraining Mutation
  const retrainMutation = useMutation({
    mutationFn: async (payload: { force: boolean; replay_ratio: number }) => {
      const { data } = await api.post('/learning/retrain', payload);
      return data;
    },
    onSuccess: (data: RetrainingJob) => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'jobs'] });
      setShowRetrainModal(false);
      addToast({
        type: 'success',
        title: 'Retraining Triggered',
        message: `Job ${data.id.slice(0, 8)} started with dataset size ${data.dataset_size}.`,
      });
    },
    onError: (err: any) => {
      addToast({
        type: 'error',
        title: 'Retraining Failed',
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  // Trigger Drift Check Mutation
  const driftCheckMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/learning/drift/check');
      return data;
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'drift'] });
      addToast({
        type: 'info',
        title: 'Drift Check Completed',
        message: data.message || `Analyzed ${data.features_tested ?? 0} features.`,
      });
    },
    onError: (err: any) => {
      addToast({
        type: 'error',
        title: 'Drift Check Failed',
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  // Promote Model Mutation
  const promoteMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const { data } = await api.post(`/learning/jobs/${jobId}/promote`);
      return data;
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'jobs'] });
      addToast({
        type: 'success',
        title: 'Candidate Promoted',
        message: data.message || 'Model promoted to Active Champion deployment.',
      });
    },
    onError: (err: any) => {
      addToast({
        type: 'error',
        title: 'Promotion Failed',
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  // Reject Model Mutation
  const rejectMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const { data } = await api.post(`/learning/jobs/${jobId}/reject`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'jobs'] });
      addToast({
        type: 'info',
        title: 'Candidate Rejected',
        message: 'Challenger model rejected. Existing Champion retained.',
      });
    },
    onError: (err: any) => {
      addToast({
        type: 'error',
        title: 'Rejection Failed',
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  const activeChampion = models.find((m) => m.status === 'active');
  const candidateModel = models.find((m) => m.status === 'candidate');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <BrainCircuit className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <span>ML Models &amp; Adaptive Learning</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Continuous model refinement: Champion/Challenger evaluation, statistical feature drift detection, and human feedback replay.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              refetchModels();
              refetchJobs();
              refetchDrift();
            }}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>

          {!isViewer && (
            <button
              onClick={() => driftCheckMutation.mutate()}
              disabled={driftCheckMutation.isPending}
              className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors"
            >
              <Activity className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>{driftCheckMutation.isPending ? 'Testing Drift…' : 'Run Drift Check'}</span>
            </button>
          )}

          {isAdmin && (
            <button
              onClick={() => setShowRetrainModal(true)}
              className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Trigger Retraining</span>
            </button>
          )}
        </div>
      </div>

      {/* Champion vs Candidate Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Champion Model */}
        <Card className="p-5 border-l-4 border-l-indigo-600 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Award className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Active Champion Model
              </h2>
            </div>
            <Badge variant="success">In Production</Badge>
          </div>

          {activeChampion ? (
            <div className="space-y-4">
              <div className="flex items-baseline justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div>
                  <span className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    {activeChampion.name}
                  </span>
                  <span className="ml-2 text-xs text-slate-400">v{activeChampion.version}</span>
                </div>
                <Badge variant="outline">{activeChampion.task}</Badge>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Macro F1</span>
                  <div className="text-lg font-bold font-mono text-indigo-600 dark:text-indigo-400">
                    {activeChampion.metrics?.macro_f1 !== undefined
                      ? (activeChampion.metrics.macro_f1 * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Precision</span>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
                    {activeChampion.metrics?.precision !== undefined
                      ? (activeChampion.metrics.precision * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Recall</span>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
                    {activeChampion.metrics?.recall !== undefined
                      ? (activeChampion.metrics.recall * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Inference Latency:</span>
                <span className="font-mono font-semibold">
                  {activeChampion.metrics?.inference_latency_ms
                    ? `${activeChampion.metrics.inference_latency_ms.toFixed(2)} ms`
                    : '< 1.50 ms'}
                </span>
              </div>
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-slate-400">
              No active champion model deployed. Run training pipeline.
            </div>
          )}
        </Card>

        {/* Challenger / Candidate Model */}
        <Card className="p-5 border-l-4 border-l-amber-500 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <GitCompare className="h-5 w-5 text-amber-500" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Challenger Candidate
              </h2>
            </div>
            {candidateModel ? (
              <Badge variant="warning">Ready for Promotion</Badge>
            ) : (
              <Badge variant="neutral">No Candidate</Badge>
            )}
          </div>

          {candidateModel ? (
            <div className="space-y-4">
              <div className="flex items-baseline justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div>
                  <span className="text-base font-bold font-mono text-slate-900 dark:text-slate-100">
                    {candidateModel.name}
                  </span>
                  <span className="ml-2 text-xs text-slate-400">v{candidateModel.version}</span>
                </div>
                <Badge variant="outline">{candidateModel.task}</Badge>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Macro F1</span>
                  <div className="text-lg font-bold font-mono text-amber-600 dark:text-amber-400">
                    {candidateModel.metrics?.macro_f1 !== undefined
                      ? (candidateModel.metrics.macro_f1 * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Precision</span>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
                    {candidateModel.metrics?.precision !== undefined
                      ? (candidateModel.metrics.precision * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg">
                  <span className="text-[11px] text-slate-400">Recall</span>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
                    {candidateModel.metrics?.recall !== undefined
                      ? (candidateModel.metrics.recall * 100).toFixed(1) + '%'
                      : 'N/A'}
                  </div>
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Trained on fresh telemetry and analyst feedback replay buffers.
              </p>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-400">
              No new candidate model awaiting promotion. Trigger retraining when drift is flagged or analyst feedback accumulates.
            </div>
          )}
        </Card>
      </div>

      {/* Retraining Jobs Table */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Model Retraining History &amp; Promotion Pipeline
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Auditable lifecycle records for model retraining, replay validation, and champion promotions.
            </p>
          </div>
        </div>

        {jobsLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading retraining records…</div>
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={BrainCircuit}
            title="No Retraining Jobs Executed"
            description="Trigger a retraining job above using collected telemetry and analyst feedback labels."
          />
        ) : (
          <DataTable
            data={jobs}
            searchPlaceholder="Filter retraining jobs…"
            searchColumn="status"
            columns={[
              {
                header: 'Created At',
                accessor: 'created_at',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                    {format(new Date(row.created_at), 'yyyy-MM-dd HH:mm')}
                  </span>
                ),
              },
              {
                header: 'Status',
                accessor: 'status',
                cell: (row) => {
                  if (row.status === 'promoted') return <Badge variant="success">Promoted to Active</Badge>;
                  if (row.status === 'candidate_ready') return <Badge variant="warning">Candidate Ready</Badge>;
                  if (row.status === 'running') return <Badge variant="indigo">Running Training…</Badge>;
                  if (row.status === 'rejected') return <Badge variant="neutral">Rejected</Badge>;
                  return <Badge variant="outline">{row.status}</Badge>;
                },
              },
              {
                header: 'Dataset Size',
                accessor: 'dataset_size',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
                    {row.dataset_size.toLocaleString()} samples
                  </span>
                ),
              },
              {
                header: 'Completed At',
                accessor: 'completed_at',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-500">
                    {row.completed_at ? format(new Date(row.completed_at), 'HH:mm:ss') : '—'}
                  </span>
                ),
              },
              {
                header: 'Promotion Gate',
                accessor: 'id',
                cell: (row) =>
                  isAdmin && row.status === 'candidate_ready' ? (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() =>
                          setConfirmState({
                            isOpen: true,
                            title: 'Promote Candidate to Champion?',
                            description: 'This will replace the active production model with this candidate challenger.',
                            onConfirm: () => promoteMutation.mutate(row.id),
                          })
                        }
                        className="flex items-center space-x-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-medium"
                      >
                        <Check className="h-3 w-3" />
                        <span>Promote</span>
                      </button>
                      <button
                        onClick={() =>
                          setConfirmState({
                            isOpen: true,
                            title: 'Reject Candidate?',
                            description: 'This will discard this candidate challenger and maintain the existing model.',
                            onConfirm: () => rejectMutation.mutate(row.id),
                          })
                        }
                        className="flex items-center space-x-1 px-2.5 py-1 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 text-slate-700 dark:text-slate-200 rounded text-xs font-medium"
                      >
                        <X className="h-3 w-3" />
                        <span>Reject</span>
                      </button>
                    </div>
                  ) : null,
              },
            ]}
          />
        )}
      </Card>

      {/* Feature Drift Detection Events */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Statistical Feature &amp; Concept Drift Audit
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Monitored drift across packet/flow distributions (Kolmogorov-Smirnov &amp; Wasserstein statistical tests).
            </p>
          </div>
        </div>

        {driftLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading drift analysis…</div>
        ) : driftEvents.length === 0 ? (
          <EmptyState
            icon={Zap}
            title="Zero Drift Events Detected"
            description="Statistical distribution of input features is currently aligned with model training baselines."
          />
        ) : (
          <DataTable
            data={driftEvents}
            searchPlaceholder="Filter drifted feature…"
            searchColumn="feature_name"
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
                header: 'Feature Name',
                accessor: 'feature_name',
                cell: (row) => (
                  <span className="font-mono text-xs font-semibold text-slate-900 dark:text-slate-100">
                    {row.feature_name}
                  </span>
                ),
              },
              {
                header: 'Drift Score (Distance)',
                accessor: 'drift_score',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
                    {row.drift_score.toFixed(4)}
                  </span>
                ),
              },
              {
                header: 'P-Value',
                accessor: 'p_value',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-500">
                    {row.p_value !== undefined ? row.p_value.toFixed(4) : '—'}
                  </span>
                ),
              },
              {
                header: 'Drift Detected',
                accessor: 'is_drift',
                cell: (row) => (
                  <Badge variant={row.is_drift ? 'danger' : 'success'}>
                    {row.is_drift ? 'Drift Alert' : 'Baseline OK'}
                  </Badge>
                ),
              },
            ]}
          />
        )}
      </Card>

      {/* Retraining Configuration Modal */}
      {showRetrainModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md p-6 space-y-4 shadow-xl">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
              <Sliders className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <span>Configure Retraining Pipeline</span>
            </h2>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  <span>Replay Buffer Ratio (Historical vs Fresh)</span>
                  <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {(replayRatio * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.5"
                  step="0.05"
                  value={replayRatio}
                  onChange={(e) => setReplayRatio(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Prevents catastrophic forgetting by blending historical baseline flows.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  id="force"
                  type="checkbox"
                  checked={forceRetrain}
                  onChange={(e) => setForceRetrain(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="force" className="text-xs text-slate-700 dark:text-slate-300">
                  Force retrain even if new sample count threshold is not met
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowRetrainModal(false)}
                className="px-3 py-2 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  retrainMutation.mutate({ force: forceRetrain, replay_ratio: replayRatio })
                }
                disabled={retrainMutation.isPending}
                className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 transition-colors"
              >
                {retrainMutation.isPending ? 'Starting Pipeline…' : 'Start Retraining'}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        description={confirmState.description}
        onConfirm={() => {
          confirmState.onConfirm();
          setConfirmState((s) => ({ ...s, isOpen: false }));
        }}
        onCancel={() => setConfirmState((s) => ({ ...s, isOpen: false }))}
      />
    </div>
  );
}

