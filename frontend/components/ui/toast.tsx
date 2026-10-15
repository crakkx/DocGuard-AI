"use client";

import * as React from "react";
import { CheckCircle2, XCircle, X, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastVariant = "default" | "success" | "error";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (t: { title: string; description?: string; variant?: ToastVariant }) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);
  const idRef = React.useRef(0);

  const toast = React.useCallback(
    ({ title, description, variant = "default" }: Omit<ToastItem, "id" | "variant"> & { variant?: ToastVariant }) => {
      const id = ++idRef.current;
      setItems((prev) => [...prev, { id, title, description, variant }]);
      setTimeout(() => {
        setItems((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[100] flex w-full max-w-sm flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-xl border bg-white p-4 shadow-lg animate-fade-up",
              t.variant === "success" && "border-green-200",
              t.variant === "error" && "border-red-200",
              t.variant === "default" && "border-[var(--border)]"
            )}
          >
            {t.variant === "success" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />}
            {t.variant === "error" && <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />}
            {t.variant === "default" && <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />}
            <div className="flex-1 text-sm">
              <p className="font-semibold text-[var(--text-primary)]">{t.title}</p>
              {t.description && <p className="mt-0.5 text-xs text-[var(--text-muted)]">{t.description}</p>}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="rounded-md p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
