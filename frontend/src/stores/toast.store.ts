import { create } from "zustand";

export type ToastVariant = "success" | "error" | "info";

export interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastState {
  toasts: Toast[];
  show: (message: string, variant?: ToastVariant) => void;
  dismiss: (id: number) => void;
}

let nextId = 1;
const TOAST_TTL_MS = 4000;

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  show: (message, variant = "info") => {
    const id = nextId++;
    set((state) => ({ toasts: [...state.toasts, { id, message, variant }] }));
    setTimeout(() => get().dismiss(id), TOAST_TTL_MS);
  },
  dismiss: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
