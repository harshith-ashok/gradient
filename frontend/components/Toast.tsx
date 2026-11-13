"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

type Kind = "info" | "success" | "error";
type Item = { id: number; message: string; kind: Kind };
const Ctx = createContext<(message: string, kind?: Kind, ms?: number) => void>(() => {});

export const useToast = () => useContext(Ctx);

let counter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const toast = useCallback((message: string, kind: Kind = "info", ms = 4500) => {
    const id = ++counter;
    setItems((xs) => [...xs, { id, message, kind }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), ms);
  }, []);
  const value = useMemo(() => toast, [toast]);
  const tone: Record<Kind, string> = {
    info: "bg-primary text-white",
    success: "bg-success text-white",
    error: "bg-destructive text-white",
  };
  return (
    <Ctx.Provider value={value}>
      {children}
      <div role="status" aria-live="polite" className="fixed bottom-6 right-6 z-50 flex max-w-sm flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className={`rounded-md px-4 py-3 text-sm shadow-lg ${tone[t.kind]}`}>{t.message}</div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
