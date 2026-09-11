import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "@/components/Providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "CareerLens | AI-Powered Career Intelligence",
  description: "Transform your career with AI-powered job matching, CV analysis, and personalized recommendations. Find opportunities that truly fit your skills.",
  keywords: ["AI jobs", "career intelligence", "CV analysis", "job matching", "hiring platform"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.variable} min-h-screen bg-neutral-900 text-neutral-50 antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
