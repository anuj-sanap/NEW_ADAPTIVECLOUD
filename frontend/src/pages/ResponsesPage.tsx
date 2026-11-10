// frontend/src/pages/ResponsesPage.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  ShieldAlert,
  RotateCcw,
  Plus,
  Trash2,
  Undo2,
  Check,
  AlertCircle,
  Sliders,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import api from '@/api/client';
import { BlocklistEntry, PolicyConfig, ResponseAction } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useToast } from '@/components/ui/Toast';
import { useAuthStore } from '@/store/authStore';
import { format } from 'date-fns';

export default function ResponsesPage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const isViewer = useAuthStore((s) => s.isViewer);

  // Block modal state
  const [showAddBlock, setShowAddBlock] = useState(false);
  const [newIp, setNewIp] = useState('');
  const [newReason, setNewReason] = useState('');
  const [newTtl, setNewTtl] = useState(60);

  // Confirmation state
  const [confirmAction, setConfirmAction] = useState<{
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

  // 1. Fetch Response Actions
  const {
    data: actions = [],
    isLoading: actionsLoading,
    refetch: refetchActions,
  } = useQuery<ResponseAction[]>({
    queryKey: ['responses'],
    queryFn: async () => {
      const { data } = await api.get('/responses', { params: { limit: 100 } });
      return data;
    },
    refetchInterval: 10000,
  });

  // 2. Fetch Policy Config
  const {
    data: policy,
    isLoading: policyLoading,
  } = useQuery<PolicyConfig>({
    queryKey: ['responses', 'policy'],
    queryFn: async () => {
      const { data } = await api.get('/responses/policy');
      return data;
    },
  });

  // 3. Fetch Blocklist
  const {
    data: blocklist = [],
    isLoading: blocklistLoading,
    refetch: refetchBlocklist,
  } = useQuery<BlocklistEntry[]>({
    queryKey: ['blocklist'],
    queryFn: async () => {
      const { data } = await api.get('/blocklist', { params: { limit: 100 } });
      return data;
    },
    refetchInterval: 15000,
  });

  // Mutation: Approve Action
  const approveMutation = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/responses/${id}/approve`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['responses'] });
      addToast({ type: 'success', title: 'Countermeasure Approved', message: 'Action queued for immediate dispatch.' });
    },
    onError: (err: any) => {
      addToast({ type: 'error', title: 'Approval Failed', message: err.response?.data?.detail || err.message });
    },
  });

  // Mutation: Rollback Action
  const rollbackMutation = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/responses/${id}/rollback`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['responses'] });
      queryClient.invalidateQueries({ queryKey: ['blocklist'] });
      addToast({ type: 'info', title: 'Countermeasure Rolled Back', message: 'Defensive rule reversed successfully.' });
    },
    onError: (err: any) => {
      addToast({ type: 'error', title: 'Rollback Failed', message: err.response?.data?.detail || err.message });
    },
  });

  // Mutation: Add Blocklist IP
  const addBlockMutation = useMutation({
    mutationFn: async (payload: { ip: string; reason: string; ttl_minutes: number }) => {
      const { data } = await api.post('/blocklist', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocklist'] });
      setShowAddBlock(false);
      setNewIp('');
      setNewReason('');
      addToast({ type: 'success', title: 'IP Blocked', message: 'Firewall drop rule applied to target host.' });
    },
    onError: (err: any) => {
      addToast({ type: 'error', title: 'Block Failed', message: err.response?.data?.detail || err.message });
    },
  });

  // Mutation: Remove Blocklist IP
  const removeBlockMutation = useMutation({
    mutationFn: async (target: string) => {
      const { data } = await api.delete(`/blocklist/${target}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocklist'] });
      addToast({ type: 'info', title: 'IP Unblocked', message: 'Address removed from firewall blacklist.' });
    },
    onError: (err: any) => {
      addToast({ type: 'error', title: 'Unblock Failed', message: err.response?.data?.detail || err.message });
    },
  });

  // Mutation: Toggle Dry-Run
  const updatePolicyMutation = useMutation({
    mutationFn: async (updated: Partial<PolicyConfig>) => {
      const { data } = await api.put('/responses/policy', updated);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['responses', 'policy'] });
      addToast({ type: 'success', title: 'Policy Updated', message: 'Response engine safety thresholds refreshed.' });
    },
    onError: (err: any) => {
      addToast({ type: 'error', title: 'Policy Update Failed', message: err.response?.data?.detail || err.message });
    },
  });

  // Filter pending approvals
  const pendingApprovals = actions.filter((a) => a.status === 'pending');

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge variant="success">Verified Active</Badge>;
      case 'executed':
        return <Badge variant="indigo">Executed</Badge>;
      case 'pending':
        return <Badge variant="warning">Awaiting Approval</Badge>;
      case 'rolled_back':
        return <Badge variant="neutral">Rolled Back</Badge>;
      case 'failed':
        return <Badge variant="danger">Execution Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <ShieldCheck className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <span>Response &amp; Recovery</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Autonomous and analyst-approved defensive countermeasures: IP blocklists, rate limiting, and process quarantine.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              refetchActions();
              refetchBlocklist();
            }}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Refresh State</span>
          </button>

          {!isViewer && (
            <button
              onClick={() => setShowAddBlock(true)}
              className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Block Remote IP</span>
            </button>
          )}
        </div>
      </div>

      {/* Safety Policy & Engine Status Banner */}
      {policy && (
        <Card className="p-4 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <Sliders className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <div>
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                  Engine Operating Mode:
                </span>
                <span className="ml-2 text-xs font-mono font-bold">
                  {policy.dry_run ? (
                    <span className="text-amber-600 dark:text-amber-400">Dry-Run (Simulated Only)</span>
                  ) : (
                    <span className="text-emerald-600 dark:text-emerald-400">Live Enforcement (Enforced via Windows Firewall)</span>
                  )}
                </span>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Rate limit: max {policy.max_actions_per_minute} actions/min &bull; Protected IPs: {policy.never_block_ips?.length ?? 0}
                </p>
              </div>
            </div>

            {!isViewer && (
              <button
                onClick={() =>
                  setConfirmAction({
                    isOpen: true,
                    title: policy.dry_run ? 'Enable Live Enforcement?' : 'Enable Dry-Run Mode?',
                    description: policy.dry_run
                      ? 'Live enforcement will dispatch real Netsh firewall drop rules on Windows cloud workers.'
                      : 'Dry-run mode simulates and logs countermeasures without modifying firewall rules.',
                    onConfirm: () => updatePolicyMutation.mutate({ dry_run: !policy.dry_run }),
                  })
                }
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Switch to {policy.dry_run ? 'Live Enforcement' : 'Dry-Run Mode'}
              </button>
            )}
          </div>
        </Card>
      )}

      {/* Approvals Queue */}
      {pendingApprovals.length > 0 && (
        <Card className="border-amber-200 dark:border-amber-900/60 bg-amber-50/30 dark:bg-amber-950/20 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Action Approvals Queue ({pendingApprovals.length})
              </h2>
            </div>
            <span className="text-xs text-amber-700 dark:text-amber-300 font-medium">
              High-impact countermeasures awaiting analyst authorization
            </span>
          </div>

          <div className="space-y-3">
            {pendingApprovals.map((act) => (
              <div
                key={act.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-white dark:bg-slate-900 border border-amber-200/60 dark:border-amber-900/40 gap-3"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100 uppercase">
                      {act.action.replace('_', ' ')}
                    </span>
                    <Badge variant="warning">Target: {act.target}</Badge>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Initiated by {act.initiated_by} &bull; Queued{' '}
                    {format(new Date(act.created_at), 'HH:mm:ss')}
                  </p>
                </div>

                {!isViewer && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() =>
                        setConfirmAction({
                          isOpen: true,
                          title: `Approve ${act.action}?`,
                          description: `This will execute the countermeasure '${act.action}' against target '${act.target}' immediately.`,
                          onConfirm: () => approveMutation.mutate(act.id),
                        })
                      }
                      disabled={approveMutation.isPending}
                      className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition-colors"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Authorize</span>
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Dynamic Firewall Blocklist */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Active Host Blocklist
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Live malicious IP addresses blocked across Windows host firewalls.
            </p>
          </div>
        </div>

        {blocklistLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading blocklist entries…</div>
        ) : blocklist.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Firewall Blocklist is Empty"
            description="No malicious IP addresses are currently blocked by automated or manual rules."
          />
        ) : (
          <DataTable
            data={blocklist}
            searchPlaceholder="Search IP address…"
            searchColumn="ip"
            columns={[
              {
                header: 'Blocked IP Address',
                accessor: 'ip',
                cell: (row) => (
                  <span className="font-mono text-xs font-semibold text-rose-600 dark:text-rose-400">
                    {row.ip}
                  </span>
                ),
              },
              {
                header: 'Reason',
                accessor: 'reason',
                cell: (row) => (
                  <span className="text-xs text-slate-700 dark:text-slate-300">
                    {row.reason || 'Automated IDS countermeasure'}
                  </span>
                ),
              },
              {
                header: 'Status',
                accessor: 'active',
                cell: (row) => (
                  <Badge variant={row.active ? 'danger' : 'neutral'}>
                    {row.active ? 'Enforced' : 'Expired'}
                  </Badge>
                ),
              },
              {
                header: 'Expiration / TTL',
                accessor: 'expires_at',
                cell: (row) => (
                  <span className="text-xs font-mono text-slate-500">
                    {row.expires_at ? format(new Date(row.expires_at), 'yyyy-MM-dd HH:mm') : 'Permanent'}
                  </span>
                ),
              },
              {
                header: 'Actions',
                accessor: 'id',
                cell: (row) =>
                  !isViewer && row.active ? (
                    <button
                      onClick={() =>
                        setConfirmAction({
                          isOpen: true,
                          title: `Unblock ${row.ip}?`,
                          description: `This will remove the drop rule from all Windows worker host firewalls.`,
                          onConfirm: () => removeBlockMutation.mutate(row.ip),
                        })
                      }
                      className="flex items-center space-x-1 text-xs text-rose-600 dark:text-rose-400 hover:underline"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      <span>Unblock</span>
                    </button>
                  ) : null,
              },
            ]}
          />
        )}
      </Card>

      {/* Countermeasure Execution Log */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Countermeasure Action Audit Log
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Complete pipeline tracking: Pending &rarr; Executed &rarr; Verified &bull; With one-click rollback.
            </p>
          </div>
        </div>

        {actionsLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading countermeasure audit log…</div>
        ) : actions.length === 0 ? (
          <EmptyState
            icon={ShieldAlert}
            title="No Countermeasure Actions"
            description="Zero defensive actions recorded. Trigger a response or adjust severity policy thresholds."
          />
        ) : (
          <DataTable
            data={actions}
            searchPlaceholder="Filter actions…"
            searchColumn="target"
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
                  <span className="font-semibold text-xs font-mono uppercase text-slate-900 dark:text-slate-100">
                    {row.action.replace('_', ' ')}
                  </span>
                ),
              },
              {
                header: 'Target Resource',
                accessor: 'target',
                cell: (row) => (
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-300 font-medium">
                    {row.target}
                  </span>
                ),
              },
              {
                header: 'Initiated By',
                accessor: 'initiated_by',
                cell: (row) => (
                  <span className="text-xs text-slate-500">{row.initiated_by}</span>
                ),
              },
              {
                header: 'Status',
                accessor: 'status',
                cell: (row) => getStatusBadge(row.status),
              },
              {
                header: 'Rollback',
                accessor: 'id',
                cell: (row) =>
                  !isViewer && (row.status === 'executed' || row.status === 'verified') ? (
                    <button
                      onClick={() =>
                        setConfirmAction({
                          isOpen: true,
                          title: `Rollback Countermeasure?`,
                          description: `This will reverse action '${row.action}' for target '${row.target}'.`,
                          onConfirm: () => rollbackMutation.mutate(row.id),
                        })
                      }
                      className="flex items-center space-x-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <Undo2 className="h-3.5 w-3.5" />
                      <span>Rollback</span>
                    </button>
                  ) : null,
              },
            ]}
          />
        )}
      </Card>

      {/* Add Block Modal */}
      {showAddBlock && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md p-6 space-y-4 shadow-xl">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
              <Lock className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <span>Add IP to Firewall Blocklist</span>
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  IPv4 / IPv6 Address
                </label>
                <input
                  type="text"
                  placeholder="e.g. 192.168.1.100"
                  value={newIp}
                  onChange={(e) => setNewIp(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Reason / Attribution
                </label>
                <input
                  type="text"
                  placeholder="e.g. Brute-force SSH attack detected"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Duration (TTL Minutes)
                </label>
                <input
                  type="number"
                  min={5}
                  value={newTtl}
                  onChange={(e) => setNewTtl(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowAddBlock(false)}
                className="px-3 py-2 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!newIp.trim()) return;
                  addBlockMutation.mutate({
                    ip: newIp.trim(),
                    reason: newReason.trim() || 'Manual firewall block',
                    ttl_minutes: newTtl,
                  });
                }}
                disabled={addBlockMutation.isPending || !newIp.trim()}
                className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 transition-colors"
              >
                {addBlockMutation.isPending ? 'Blocking…' : 'Enforce Block'}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmAction.isOpen}
        title={confirmAction.title}
        description={confirmAction.description}
        onConfirm={() => {
          confirmAction.onConfirm();
          setConfirmAction((s) => ({ ...s, isOpen: false }));
        }}
        onCancel={() => setConfirmAction((s) => ({ ...s, isOpen: false }))}
      />
    </div>
  );
}

