"use client";

import { motion, AnimatePresence } from "framer-motion";

type DialogType = "info" | "success" | "error" | "warning";

interface MessageDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  message: string;
  type?: DialogType;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
}

export default function MessageDialog({
  open,
  onClose,
  title,
  message,
  type = "info",
  confirmText = "OK",
  cancelText = "Cancel",
  onConfirm,
}: MessageDialogProps) {
  if (!open) return null;

  const typeStyles: Record<
    DialogType,
    { icon: string; iconBg: string; buttonClass: string }
  > = {
    info: {
      icon: "i",
      iconBg: "bg-blue-600/20 text-blue-400",
      buttonClass:
        "bg-gradient-to-r from-blue-600 to-emerald-500 text-white hover:shadow-lg hover:shadow-blue-500/25",
    },
    success: {
      icon: "✓",
      iconBg: "bg-emerald-500/20 text-emerald-400",
      buttonClass:
        "bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:shadow-lg hover:shadow-emerald-500/25",
    },
    error: {
      icon: "!",
      iconBg: "bg-rose-500/20 text-rose-400",
      buttonClass:
        "bg-gradient-to-r from-rose-500 to-red-600 text-white hover:shadow-lg hover:shadow-rose-500/25",
    },
    warning: {
      icon: "!",
      iconBg: "bg-amber-500/20 text-amber-400",
      buttonClass:
        "bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:shadow-lg hover:shadow-amber-500/25",
    },
  };

  const styles = typeStyles[type];

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-sm rounded-lg bg-neutral-800 border border-neutral-700/50 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-start gap-4">
                <div
                  className={`w-10 h-10 rounded-lg ${styles.iconBg} flex items-center justify-center flex-shrink-0 font-bold text-lg`}
                >
                  {styles.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-neutral-50">
                    {title}
                  </h3>
                  <p className="text-sm text-neutral-400 mt-1 leading-relaxed">
                    {message}
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                {onConfirm !== undefined && (
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-neutral-400 hover:text-neutral-200 hover:bg-neutral-700/50 rounded-lg transition-colors"
                  >
                    {cancelText}
                  </button>
                )}
                <motion.button
                  onClick={handleConfirm}
                  className={`px-5 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${styles.buttonClass}`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {confirmText}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
