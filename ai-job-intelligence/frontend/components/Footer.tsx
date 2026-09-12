"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { EXTERNAL_LINK_PROPS, SOCIAL_LINKS } from "@/components/site";
import {
  FaBriefcase,
} from "react-icons/fa";

const footerLinks = {
  product: [
    { label: "Features", href: "/#features" },
    { label: "Pricing", href: "/pricing" },
    { label: "For Employers", href: "/#for-employers" },
    { label: "For Job Seekers", href: "/#for-job-seekers" },
  ],
  company: [
    { label: "About", href: "/about" },
    { label: "How it Works", href: "/how-it-works" },
    { label: "Contact", href: "/contact" },
  ],
  resources: [
    { label: "FAQ", href: "/faq" },
    { label: "Help Center", href: "/contact" },
    { label: "Privacy Policy", href: "/about" },
    { label: "Terms of Service", href: "/about" },
  ],
};

export default function Footer() {
  const router = useRouter();

  return (
    <footer className="relative bg-neutral-950 border-t border-neutral-800/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12">
          <div className="lg:col-span-2">
            <motion.div
              className="flex items-center gap-3 mb-4 cursor-pointer"
              onClick={() => router.push("/")}
              whileHover={{ scale: 1.02 }}
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
                <span className="text-white font-black text-lg">C</span>
              </div>
              <span className="text-xl font-bold text-neutral-50">
                Career<span className="text-blue-400">Lens</span>
              </span>
            </motion.div>
            <p className="text-neutral-400 text-sm leading-relaxed max-w-sm mb-6">
              AI-powered career intelligence that connects talent with opportunity.
              Find jobs that truly fit your skills and potential.
            </p>
            <div className="flex items-center gap-4">
              {SOCIAL_LINKS.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  aria-label={social.label}
                  {...EXTERNAL_LINK_PROPS}
                  className="w-10 h-10 rounded-lg bg-neutral-800/50 border border-neutral-700/50 flex items-center justify-center text-neutral-400 hover:text-neutral-50 hover:bg-neutral-800 hover:border-neutral-600 transition-all duration-200"
                >
                  <social.icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">
              Product
            </h4>
            <ul className="space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-neutral-400 hover:text-neutral-200 text-sm transition-colors duration-200"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">
              Company
            </h4>
            <ul className="space-y-3">
              {footerLinks.company.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-neutral-400 hover:text-neutral-200 text-sm transition-colors duration-200"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">
              Resources
            </h4>
            <ul className="space-y-3">
              {footerLinks.resources.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-neutral-400 hover:text-neutral-200 text-sm transition-colors duration-200"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-neutral-800/50">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-neutral-500 text-sm">
              &copy; {new Date().getFullYear()} CareerLens. All rights reserved.
            </p>
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <FaBriefcase className="w-4 h-4 text-blue-400" />
              <span>AI-powered career intelligence</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
