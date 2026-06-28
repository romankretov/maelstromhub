import Link from "next/link";
import { Database } from "lucide-react";

import { PageShell } from "@/components/shell/page-shell";

const adminLinks = [
  {
    title: "Research Overview",
    href: "/research",
    description: "Legacy research workflow overview.",
  },
  {
    title: "Assets",
    href: "/research/assets",
    description: "Backend asset records used to resolve markets.",
  },
  {
    title: "Timeframes",
    href: "/research/timeframes",
    description: "Internal system interval records.",
  },
  {
    title: "Datasets",
    href: "/research/datasets",
    description: "Backend market data containers.",
  },
  {
    title: "Features",
    href: "/research/features",
    description: "Feature definitions and computed stats metadata.",
  },
  {
    title: "Experiments",
    href: "/research/experiments",
    description: "Legacy research experiment records.",
  },
];

export default function AdvancedDataAdminPage() {
  return (
    <PageShell
      title="Advanced Data Admin"
      description="Internal access to legacy backend data objects. Normal research should happen in Workspace."
    >
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {adminLinks.map((link) => (
          <Link key={link.href} href={link.href} className="rounded-lg border bg-card p-5 transition-colors hover:bg-muted">
            <Database className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="mt-4 text-base font-semibold">{link.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{link.description}</p>
          </Link>
        ))}
      </section>
    </PageShell>
  );
}
