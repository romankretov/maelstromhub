import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
};

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <section className="rounded-lg border bg-card p-8 text-card-foreground">
      <Icon className="h-8 w-8 text-primary" aria-hidden="true" />
      <h2 className="mt-5 text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
  );
}
