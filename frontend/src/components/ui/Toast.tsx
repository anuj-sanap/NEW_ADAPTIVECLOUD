// frontend/src/components/ui/Toast.tsx
import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
}

export interface ToastPayload {
  type?: ToastType;
  title?: string;
  message: string;
}

export interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
  addToast: (payload: ToastPayload) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((payload: ToastPayload) => {
    const id = Math.random().toString(36).substring(2, 9);
    const item: ToastItem = {
      id,
      type: payload.type || 'info',
      title: payload.title,
      message: payload.message,
    };
    setToasts((prev) => [...prev, item]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'info') => {
      addToast({ message, type });
    },
    [addToast]
  );

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast, addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start space-x-3 p-3 rounded-xl border shadow-lg text-xs font-medium transition-all ${
              toast.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/80 dark:border-emerald-800 dark:text-emerald-200'
                : toast.type === 'error'
                ? 'bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-950/80 dark:border-rose-800 dark:text-rose-200'
                : toast.type === 'warning'
                ? 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/80 dark:border-amber-800 dark:text-amber-200'
                : 'bg-white border-slate-200 text-slate-800 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200'
            }`}
          >
            <div className="mt-0.5 flex-shrink-0">
              {toast.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
              {toast.type === 'error' && <AlertCircle className="h-4 w-4 text-rose-500" />}
              {toast.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-500" />}
              {toast.type === 'info' && <Info className="h-4 w-4 text-indigo-500" />}
            </div>
            <div className="flex-1 min-w-0">
              {toast.title && <div className="font-semibold text-xs mb-0.5">{toast.title}</div>}
              <div className="text-[11px] leading-relaxed opacity-90">{toast.message}</div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
