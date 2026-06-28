import {
  Activity,
  FlaskConical,
  Gauge,
  MonitorCog,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export const workflowSteps = [
  "Idea",
  "Research",
  "Strategy Builder",
  "Backtest Studio",
  "Paper Deploy",
  "Deployment Center",
  "Monitor",
] as const;

export const strategyStatuses = [
  "Draft",
  "Backtested",
  "Paper Trading",
  "Live Small Size",
  "Live Full Size",
  "Paused",
  "Retired",
] as const;

export const navigationItems = [
  { title: "Workspace", href: "/workspace", icon: Gauge },
  { title: "Strategy Lab", href: "/strategy-builder", icon: FlaskConical },
  { title: "Deploy", href: "/paper-trading", icon: Activity },
  { title: "Monitor", href: "/monitor", icon: MonitorCog },
  { title: "Settings", href: "/settings", icon: Settings },
] as const;

type SafetyNote = {
  label: string;
  value: string;
  icon?: LucideIcon;
};

export const safetyNotes: SafetyNote[] = [
  { label: "Market data", value: "Not connected" },
  { label: "Backtesting", value: "Not implemented" },
  { label: "Live trading", value: "Blocked by design", icon: ShieldCheck },
];
