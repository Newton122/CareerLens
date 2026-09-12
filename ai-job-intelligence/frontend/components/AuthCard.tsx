"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

/**
 * The centred card used by the account pages that sit beside login:
 * forgot password, reset password and verify email. Same logo, colours and
 * input styles as the login page, without its marketing panel.
 */
export default function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-neutral-900 flex items-center justify-center px-4 py-12">
      <motion.div
        className="w-full max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-center mb-8">
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => router.push("/")}
          >
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <span className="text-white font-black text-lg">C</span>
            </div>
            <span className="text-xl font-bold text-neutral-50">
              Career<span className="text-blue-400">Lens</span>
            </span>
          </div>
        </div>

        <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-8">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-neutral-50 mb-2">{title}</h1>
            {subtitle && <p className="text-neutral-400">{subtitle}</p>}
          </div>
          {children}
        </div>
      </motion.div>
    </div>
  );
}
