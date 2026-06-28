import {
  Activity,
  FlaskConical,
  Gauge,
  Lightbulb,
  Microscope,
  MonitorCog,
  Rocket,
  Settings,
  ShieldCheck,
  TestTubeDiagonal,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export const workflowSteps = [
  "Idea",
  "Research",
  "Strategy Builder",
  "Backtest Studio",
  "Paper Trading",
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
  { title: "Dashboard", href: "/", icon: Gauge },
  { title: "Ideas Lab", href: "/ideas-lab", icon: Lightbulb },
  { title: "Research", href: "/research", icon: Microscope },
  { title: "Strategy Builder", href: "/strategy-builder", icon: FlaskConical },
  { title: "Backtest Studio", href: "/backtest-studio", icon: TestTubeDiagonal },
  { title: "Paper Trading", href: "/paper-trading", icon: Activity },
  { title: "Deployment Center", href: "/deployment-center", icon: Rocket },
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
