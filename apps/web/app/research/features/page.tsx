import { FeaturesClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchFeaturesPage() {
  return (
    <PageShell title="Feature Snapshots" description="Create and review feature snapshots linked to datasets.">
      <section className="rounded-lg border bg-card p-5">
        <h2 className="text-base font-semibold">Generated snapshots and definitions</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Dataset detail pages generate reusable feature snapshots from candles. This page remains a simple place for
          manually named feature definitions and notes while the generated snapshot workflow matures.
        </p>
      </section>
      <FeaturesClient />
    </PageShell>
  );
}
