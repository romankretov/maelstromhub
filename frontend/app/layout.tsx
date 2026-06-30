import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Maelstrom Research",
  description: "Hyperliquid perpetual market-data ingestion and research scanner"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <div className="brand">Maelstrom</div>
            <h2>Research OS</h2>
            <p className="muted">Hyperliquid perp discovery. No trading. No wallets.</p>
            <nav className="nav">
              <Link href="/">Market Scanner</Link>
              <Link href="/health">Ingestion Health</Link>
              <a href="https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api" target="_blank">HL Docs</a>
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
