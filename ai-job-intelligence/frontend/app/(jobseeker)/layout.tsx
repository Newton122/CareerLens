"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { useUnreadMessageCount } from "@/components/unreadMessages";
import VerifyEmailBanner from "@/components/VerifyEmailBanner";
import { ReactNode, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaHome,
  FaBriefcase,
  FaFileAlt,
  FaBookmark,
  FaChartLine,
  FaUpload,
  FaSignOutAlt,
  FaUser,
  FaBars,
  FaRobot,
  FaCalendarAlt,
  FaEnvelope,
} from "react-icons/fa";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: FaHome },
  { label: "Find Jobs", path: "/jobs", icon: FaBriefcase },
  { label: "My Applications", path: "/applications", icon: FaFileAlt },
  { label: "Saved Jobs", path: "/saved-jobs", icon: FaBookmark },
  { label: "Career Insights", path: "/career-insights", icon: FaChartLine },
  { label: "Interviews", path: "/interviews", icon: FaCalendarAlt },
  { label: "Messages", path: "/messages", icon: FaEnvelope },
  { label: "CareerLens Chat", path: "/career-lens", icon: FaRobot },
  { label: "My CV", path: "/cv", icon: FaUpload },
];

export default function JobSeekerLayout({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, loading, logout } = useAuth();
  // The page the mobile sidebar was opened on. It counts as open only while
  // you are still on that page, so navigating closes it -- derived during
  // render instead of an effect that resets state after every navigation.
  const [sidebarOpenOn, setSidebarOpenOn] = useState<string | null>(null);
  const isSidebarOpen = sidebarOpenOn === pathname;
  const setIsSidebarOpen = (open: boolean) => setSidebarOpenOn(open ? pathname : null);
  const unread = useUnreadMessageCount(Boolean(token));

  useEffect(() => {
    if (!loading && !token) {
      router.push("/login");
    }
  }, [token, loading, router]);


  if (loading || !token) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const sidebarContent = (
    <>
      <div className="px-4 mb-8">
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => router.push("/")}
        >
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-black text-sm">CL</span>
          </div>
          <span className="text-lg font-bold text-neutral-50">
            Career<span className="text-blue-400">Lens</span>
          </span>
        </div>
      </div>

      <nav className="space-y-1 px-3">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <motion.button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-blue-500/20 to-emerald-500/10 text-blue-400 font-medium border border-blue-500/20"
                  : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50"
              }`}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
            >
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
              {item.path.endsWith("/messages") && unread > 0 && (
                <span
                  className="ml-auto min-w-5 h-5 px-1.5 rounded-full bg-blue-500 text-white text-xs font-semibold flex items-center justify-center"
                  aria-label={`${unread} unread messages`}
                >
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </motion.button>
          );
        })}
      </nav>

      <div className="mt-8 px-3 space-y-1">
        <button
          onClick={() => router.push("/profile")}
          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50 rounded-lg transition-all duration-200"
        >
          <FaUser className="w-4 h-4" />
          <span>Profile</span>
        </button>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-neutral-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all duration-200"
        >
          <FaSignOutAlt className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-neutral-900">
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      <motion.aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-neutral-900 border-r border-neutral-700/50 py-6 overflow-y-auto transform transition-transform duration-300 lg:transform-none ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {sidebarContent}
      </motion.aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-30 bg-neutral-900/95 backdrop-blur-xl border-b border-neutral-700/50 px-4 lg:px-6 py-4 lg:hidden">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 text-neutral-400 hover:text-neutral-200 rounded-lg"
            >
              <FaBars className="w-5 h-5" />
            </button>
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => router.push("/")}
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center">
                <span className="text-white font-black text-xs">CL</span>
              </div>
              <span className="text-lg font-bold text-neutral-50">
                Career<span className="text-blue-400">Lens</span>
              </span>
            </div>
            <button
              onClick={logout}
              aria-label="Sign out"
              className="p-2 text-neutral-400 hover:text-neutral-200 rounded-lg"
            >
              <FaSignOutAlt className="w-5 h-5" />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-x-hidden px-4 lg:px-8 py-6">
          <VerifyEmailBanner />
          {children}
        </main>
      </div>
    </div>
  );
}
