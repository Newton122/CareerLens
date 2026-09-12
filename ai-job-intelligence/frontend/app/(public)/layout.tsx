"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

/**
 * Chrome for the public route group.
 *
 * Login and register are full-screen split-panel auth pages that intentionally
 * carry no marketing navigation, so they opt out. Everything else gets the same
 * Navbar/Footer the landing page uses, which previously left About, FAQ,
 * How-it-works, Contact, Pricing and Demo with no navigation at all.
 */
const CHROMELESS_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
];

export default function PublicLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (CHROMELESS_ROUTES.includes(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen flex-col bg-neutral-900">
      <Navbar />
      {/* Navbar is fixed, so reserve its height. */}
      <main className="flex-1 pt-16 lg:pt-20">{children}</main>
      <Footer />
    </div>
  );
}
