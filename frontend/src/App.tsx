// frontend/src/App.tsx
import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '@/components/ui/Toast';
import { Layout } from '@/components/layout/Layout';
import { useAuthStore } from '@/store/authStore';

// Page components
import LoginPage from '@/pages/LoginPage';
import { OverviewPage } from '@/pages/OverviewPage';
import { MonitoringPage } from '@/pages/MonitoringPage';
import { DetectionsPage } from '@/pages/DetectionsPage';
import { ClassificationsPage } from '@/pages/ClassificationsPage';
import { RcaPage } from '@/pages/RcaPage';
import ThreatPredictionPage from '@/pages/ThreatPredictionPage';
import MaintenancePage from '@/pages/MaintenancePage';
import ResponsesPage from '@/pages/ResponsesPage';
import ModelsLearningPage from '@/pages/ModelsLearningPage';
import ReportsAuditPage from '@/pages/ReportsAuditPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token || s.accessToken);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<OverviewPage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
            <Route path="/detections" element={<DetectionsPage />} />
            <Route path="/classifications" element={<ClassificationsPage />} />
            <Route path="/rca" element={<RcaPage />} />
            <Route path="/predictions" element={<ThreatPredictionPage />} />
            <Route path="/maintenance" element={<MaintenancePage />} />
            <Route path="/responses" element={<ResponsesPage />} />
            <Route path="/learning" element={<ModelsLearningPage />} />
            <Route path="/reports" element={<ReportsAuditPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ToastProvider>
    </QueryClientProvider>
  );
}
