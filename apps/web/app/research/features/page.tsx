import { Microscope } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchFeaturesPage() {
  return (
    <PageShell title="Feature Snapshots" description="Placeholder page for feature snapshots linked to datasets.">
      <EmptyState
        icon={Microscope}
        title="Feature CRUD is available in the API"
        description="Feature snapshots store research metadata and values only. No feature pipeline is implemented."
      />
    </PageShell>
  );
}
