"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/components/AuthProvider";
import {
  FaBars,
  FaTimes,
  FaRocket,
  FaSignInAlt,
  FaUserPlus,
} from "react-icons/fa";

const navLinks = [
  { label: "Features", href: "/#features", action: false },
  { label: "Pricing", href: "/pricing", action: true },
  { label: "For Employers", href: "/#for-employers", action: false },
  { label: "For Job Seekers", href: "/#for-job-seekers", action: false },
];

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { token } = useAuth();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleNavigate = (href: string) => {
    setIsMobileMenuOpen(false);
    router.push(href);
  };

  const isHomePage = pathname === "/";

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? "bg-neutral-900/95 backdrop-blur-xl border-b border-neutral-700/50"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          <motion.div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => router.push("/")}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="relative">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <span className="text-white font-black text-lg">C</span>
              </div>
              <div className="absolute -inset-1 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 opacity-20 blur-sm -z-10" />
            </div>
            <span className="text-xl font-bold text-neutral-50">
              Career<span className="text-blue-400">Lens</span>
            </span>
          </motion.div>

          {isHomePage && (
            <nav className="hidden lg:flex items-center gap-1">
              {navLinks.map((link) =>
                link.action ? (
                  <button
                    key={link.label}
                    onClick={() => router.push(link.href)}
                    className="px-4 py-2 text-sm font-medium text-neutral-400 hover:text-neutral-50 rounded-lg transition-colors duration-200"
                  >
                    {link.label}
                  </button>
                ) : (
                  <a
                    key={link.label}
                    href={link.href}
                    className="px-4 py-2 text-sm font-medium text-neutral-400 hover:text-neutral-50 rounded-lg transition-colors duration-200"
                  >
                    {link.label}
                  </a>
                )
              )}
            </nav>
          )}

          <div className="hidden lg:flex items-center gap-3">
            {token ? (
              <motion.button
                onClick={() => router.push("/dashboard")}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-neutral-300 hover:text-neutral-50 transition-colors"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <FaRocket className="w-4 h-4" />
                Dashboard
              </motion.button>
            ) : (
              <>
                <motion.button
                  onClick={() => router.push("/login")}
                  className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-neutral-300 hover:text-neutral-50 transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <FaSignInAlt className="w-4 h-4" />
                  Log in
                </motion.button>
                <motion.button
                  onClick={() => router.push("/register")}
                  className="btn-primary flex items-center gap-2 text-sm"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <FaUserPlus className="w-4 h-4" />
                  Get Started
                </motion.button>
              </>
            )}
          </div>

          <motion.button
            className="lg:hidden p-2 text-neutral-400 hover:text-neutral-50"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            whileTap={{ scale: 0.95 }}
          >
            {isMobileMenuOpen ? (
              <FaTimes className="w-6 h-6" />
            ) : (
              <FaBars className="w-6 h-6" />
            )}
          </motion.button>
        </div>
      </div>

      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="lg:hidden overflow-hidden bg-neutral-900/98 backdrop-blur-xl border-b border-neutral-700/50"
          >
            <div className="px-4 py-6 space-y-4">
              {isHomePage &&
                navLinks.map((link) =>
                  link.action ? (
                    <button
                      key={link.label}
                      onClick={() => handleNavigate(link.href)}
                      className="block px-4 py-3 text-base font-medium text-neutral-300 hover:text-neutral-50 hover:bg-neutral-800/50 rounded-lg transition-colors"
                    >
                      {link.label}
                    </button>
                  ) : (
                    <a
                      key={link.label}
                      href={link.href}
                      className="block px-4 py-3 text-base font-medium text-neutral-300 hover:text-neutral-50 hover:bg-neutral-800/50 rounded-lg transition-colors"
                    >
                      {link.label}
                    </a>
                  )
                )}
              <div className="pt-4 border-t border-neutral-700/50 space-y-3">
                {token ? (
                  <button
                    onClick={() => router.push("/dashboard")}
                    className="w-full btn-primary flex items-center justify-center gap-2"
                  >
                    <FaRocket className="w-4 h-4" />
                    Dashboard
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => router.push("/login")}
                      className="w-full btn-secondary flex items-center justify-center gap-2"
                    >
                      <FaSignInAlt className="w-4 h-4" />
                      Log in
                    </button>
                    <button
                      onClick={() => router.push("/register")}
                      className="w-full btn-primary flex items-center justify-center gap-2"
                    >
                      <FaUserPlus className="w-4 h-4" />
                      Get Started
                    </button>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
