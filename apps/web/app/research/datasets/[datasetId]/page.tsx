import { DatasetDetailClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default async function DatasetDetailPage({
  params,
}: {
  params: Promise<{ datasetId: string }>;
}) {
  const { datasetId } = await params;

  return (
    <PageShell
      title="Dataset Detail"
      description="Fill this dataset with Hyperliquid candles and inspect the stored market data."
    >
      <DatasetDetailClient datasetId={datasetId} />
    </PageShell>
  );
}
