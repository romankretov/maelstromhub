import { Activity, Database, FlaskConical, RadioTower } from "lucide-react";

import { Button } from "@/components/ui/button";

const checks = [
  { label: "API", value: "FastAPI service", icon: RadioTower },
  { label: "Research", value: "Experiment workspace", icon: FlaskConical },
  { label: "Data", value: "Postgres and Redis", icon: Database },
  { label: "Ops", value: "Worker process", icon: Activity },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <section className="border-b">
        <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Hyperliquid research suite</p>
              <h1 className="mt-2 text-4xl font-semibold tracking-normal">Maelstromhub</h1>
            </div>
            <Button variant="outline">Local preview</Button>
          </div>
          <p className="max-w-3xl text-lg leading-8 text-muted-foreground">
            A clean foundation for market research, strategy analysis, and operational workflows.
            Trading execution is intentionally out of scope for this bootstrap.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 py-8 md:grid-cols-4">
        {checks.map((item) => (
          <div key={item.label} className="rounded-lg border bg-card p-4 text-card-foreground shadow-sm">
            <item.icon className="mb-4 h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="text-sm font-medium">{item.label}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{item.value}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
