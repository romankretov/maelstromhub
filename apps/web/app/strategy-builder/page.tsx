import { PageShell } from "@/components/shell/page-shell";
import { StrategyBuilderClient } from "@/components/workflow/strategy-builder-client";

export default function StrategyBuilderPage() {
  return (
    <PageShell
      title="Strategy Builder"
      description="Turn validated ideas into explicit strategy definitions, assumptions, and lifecycle status."
    >
      <StrategyBuilderClient />
    </PageShell>
  );
}
