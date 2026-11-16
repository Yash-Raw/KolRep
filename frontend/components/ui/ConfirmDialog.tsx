"use client";

import { AlertTriangle, HelpCircle, Loader2 } from "lucide-react";
import { DialogFrame } from "@/components/ui/DialogFrame";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  variant = "danger",
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <DialogFrame onClose={isLoading ? () => {} : onCancel}>
      <div
        className="dialog-panel max-w-md p-6 space-y-4"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex items-start gap-3.5">
          {variant === "danger" ? (
            <div className="p-2.5 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
          ) : (
            <div className="p-2.5 rounded-full bg-soft text-ink shrink-0">
              <HelpCircle className="h-5 w-5" />
            </div>
          )}
          <div className="space-y-1 min-w-0">
            <h3 className="font-semibold text-base text-ink">{title}</h3>
            <p className="text-xs text-muted leading-relaxed">{description}</p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-line">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-xs font-medium text-muted hover:text-ink disabled:opacity-50 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white transition-colors disabled:opacity-50 ${
              variant === "danger"
                ? "bg-red-600 hover:bg-red-700"
                : "bg-accent hover:bg-soft"
            }`}
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>{confirmLabel}</span>
          </button>
        </div>
      </div>
    </DialogFrame>
  );
}
