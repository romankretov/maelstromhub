import Link from "next/link";
import { Database, FlaskConical, Layers, Microscope, Timer } from "lucide-react";

import { PageShell } from "@/components/shell/page-shell";

const researchObjects = [
  {
    title: "Assets",
    href: "/research/assets",
    description: "Symbols and venues that datasets will reference.",
    icon: Database,
  },
  {
    title: "Timeframes",
    href: "/research/timeframes",
    description: "Canonical intervals for research datasets.",
    icon: Timer,
  },
  {
    title: "Datasets",
    href: "/research/datasets",
    description: "Durable metadata for future market or derived research data.",
    icon: Layers,
  },
  {
    title: "Features",
    href: "/research/features",
    description: "Feature snapshots connected to datasets.",
    icon: Microscope,
  },
  {
    title: "Experiments",
    href: "/research/experiments",
    description: "Research attempts that will later connect to strategy versions and backtests.",
    icon: FlaskConical,
  },
];

export default function ResearchPage() {
  return (
    <PageShell
      title="Research"
      description="A placeholder surface for the durable research domain: assets, timeframes, datasets, feature snapshots, and experiments."
    >
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {researchObjects.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-lg border bg-card p-5 transition-colors hover:bg-muted">
            <item.icon className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="mt-4 font-semibold">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.description}</p>
          </Link>
        ))}
      </section>
    </PageShell>
  );
}
