import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppSidebar } from "@/components/shell/app-sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Maelstromhub",
  description: "A streamlined quant trading and research suite for Hyperliquid.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen bg-background">
          <AppSidebar />
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
