import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReClaw — UX Research Agent",
  description: "Local-first AI agent for UX Research",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
