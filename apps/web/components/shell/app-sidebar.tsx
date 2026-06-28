"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navigationItems } from "@/lib/product-shell";
import { cn } from "@/lib/utils";

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-56 shrink-0 flex-col border-r border-zinc-800 bg-[#080a0e] px-3 py-4 text-zinc-100 lg:w-64">
      <div className="px-2">
        <p className="text-xs font-medium uppercase text-emerald-300">Maelstrom</p>
        <p className="mt-2 text-lg font-semibold">Research Terminal</p>
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-1">
        {navigationItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100",
                active && "bg-emerald-400/10 text-emerald-200 hover:bg-emerald-400/10 hover:text-emerald-200",
              )}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>

      <div className="rounded-md border border-zinc-800 bg-black p-3 text-xs text-zinc-500">
        <p className="font-medium text-zinc-100">Execution status</p>
        <p className="mt-1">Live trading, order placement, and private keys remain unavailable.</p>
      </div>
    </aside>
  );
}
