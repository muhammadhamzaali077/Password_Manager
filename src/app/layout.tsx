import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Password Manager Health Check",
  description: "A friendly chat that scores your password hygiene out of 100.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

/**
 * Root layout — sets the viewport, ships the global stylesheet, and renders
 * the page tree. Designed mobile-first so 375 px wide stays legible
 * (Constitution V).
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-50 text-zinc-900 antialiased">{children}</body>
    </html>
  );
}
