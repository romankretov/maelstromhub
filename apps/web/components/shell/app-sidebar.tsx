"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navigationItems } from "@/lib/product-shell";
import { cn } from "@/lib/utils";

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col border-r bg-card px-4 py-5">
      <div className="px-2">
        <p className="text-xs font-medium uppercase text-muted-foreground">Maelstromhub</p>
        <p className="mt-2 text-lg font-semibold">Research Workflow</p>
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-1">
        {navigationItems.map((item) => {
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                active && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
              )}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>

      <div className="rounded-lg border bg-background p-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Execution status</p>
        <p className="mt-1">Live trading, order placement, and private keys are not implemented.</p>
      </div>
    </aside>
  );
}
