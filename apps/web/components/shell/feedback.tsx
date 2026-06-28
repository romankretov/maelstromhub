import type { LucideIcon } from "lucide-react";

type FeedbackStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
};

export function FeedbackState({ icon: Icon, title, description }: FeedbackStateProps) {
  return (
    <section className="rounded-lg border bg-card p-6 text-card-foreground">
      <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
      <h2 className="mt-4 text-base font-semibold">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <section className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">
      {label}
    </section>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-900">
      {message}
    </section>
  );
}
