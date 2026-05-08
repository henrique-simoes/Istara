import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Archive,
  Bell,
  BookOpen,
  Bot,
  Brain,
  CheckCircle,
  Diamond,
  FileStack,
  FileText,
  FlaskConical,
  History,
  LayoutDashboard,
  MessageSquare,
  Mic,
  Palette,
  RefreshCw,
  Server,
  Settings,
  Shield,
  Sparkles,
  Users,
  Wand2,
} from "lucide-react";

export type ViewId =
  | "chat"
  | "findings"
  | "laws"
  | "tasks"
  | "interviews"
  | "documents"
  | "project-settings"
  | "context"
  | "skills"
  | "agents"
  | "memory"
  | "interfaces"
  | "integrations"
  | "loops"
  | "notifications"
  | "backup"
  | "meta-hyperagent"
  | "autoresearch"
  | "history"
  | "compute"
  | "ensemble"
  | "quality"
  | "settings"
  | "admin";

export interface NavItem {
  id: ViewId;
  icon: LucideIcon;
  label: string;
  shortLabel?: string;
  adminOnly?: boolean;
  minRole?: "viewer" | "researcher" | "admin";
}

export const PRIMARY_NAV_ITEMS: NavItem[] = [
  { id: "chat", icon: Bot, label: "Chat" },
  { id: "findings", icon: Diamond, label: "Findings" },
  { id: "laws", icon: BookOpen, label: "UX Laws" },
  { id: "tasks", icon: LayoutDashboard, label: "Tasks" },
  { id: "interviews", icon: Mic, label: "Interviews" },
  { id: "documents", icon: FileStack, label: "Documents", shortLabel: "Docs" },
  { id: "context", icon: FileText, label: "Context" },
  { id: "skills", icon: Wand2, label: "Skills" },
  { id: "agents", icon: Users, label: "Agents" },
  { id: "memory", icon: Brain, label: "Memory" },
  { id: "interfaces", icon: Palette, label: "Interfaces" },
  { id: "integrations", icon: MessageSquare, label: "Integrations" },
  { id: "loops", icon: RefreshCw, label: "Loops", minRole: "researcher" },
  { id: "settings", icon: Settings, label: "Settings" },
];

export const SECONDARY_NAV_ITEMS: NavItem[] = [
  { id: "admin", icon: Shield, label: "Admin", adminOnly: true },
  { id: "autoresearch", icon: FlaskConical, label: "Autoresearch", minRole: "researcher" },
  { id: "backup", icon: Archive, label: "Backup", adminOnly: true },
  { id: "meta-hyperagent", icon: Sparkles, label: "Meta-Agent", adminOnly: true },
  { id: "compute", icon: Server, label: "Compute Pool", minRole: "researcher" },
  { id: "ensemble", icon: Activity, label: "Ensemble Health" },
  { id: "quality", icon: CheckCircle, label: "Quality Dashboard" },
  { id: "project-settings", icon: Settings, label: "Project Settings" },
  { id: "history", icon: History, label: "History" },
];

export const UTILITY_NAV_ITEMS: NavItem[] = [
  { id: "notifications", icon: Bell, label: "Notifications" },
];

export const MOBILE_PRIMARY_VIEW_IDS: ViewId[] = ["chat", "findings", "tasks", "documents"];

export const PROJECT_REQUIRED_VIEW_IDS = new Set<ViewId>([
  "chat",
  "tasks",
  "findings",
  "laws",
  "interviews",
  "documents",
  "project-settings",
  "context",
  "loops",
  "memory",
  "history",
  "interfaces",
  "autoresearch",
  "backup",
]);

const ALL_NAV_ITEMS = [...PRIMARY_NAV_ITEMS, ...SECONDARY_NAV_ITEMS, ...UTILITY_NAV_ITEMS];

export const VIEW_NAMES: Record<string, string> = ALL_NAV_ITEMS.reduce(
  (acc, item) => {
    acc[item.id] = item.label;
    return acc;
  },
  {} as Record<string, string>
);

export const SECONDARY_NAV_IDS = new Set<ViewId>(SECONDARY_NAV_ITEMS.map((item) => item.id));

function roleRank(role?: string | null): number {
  if (role === "admin") return 2;
  if (role === "researcher") return 1;
  return 0;
}

function itemAllowedForRole(item: NavItem, role?: string | null): boolean {
  if (item.adminOnly && role !== "admin") return false;
  if (item.minRole && roleRank(role) < roleRank(item.minRole)) return false;
  return true;
}

export function filterNavItemsForRole(items: NavItem[], role?: string | null): NavItem[] {
  return items.filter((item) => itemAllowedForRole(item, role));
}

export function isViewAllowed(viewId: string, role?: string | null): boolean {
  const item = ALL_NAV_ITEMS.find((candidate) => candidate.id === viewId);
  return Boolean(item && itemAllowedForRole(item, role));
}

export function mobilePrimaryItemsForRole(role?: string | null): NavItem[] {
  const primaryIds = new Set(MOBILE_PRIMARY_VIEW_IDS);
  return filterNavItemsForRole(ALL_NAV_ITEMS, role).filter((item) => primaryIds.has(item.id));
}

export function mobileMoreItemsForRole(role?: string | null): NavItem[] {
  const primaryIds = new Set(MOBILE_PRIMARY_VIEW_IDS);
  return filterNavItemsForRole(ALL_NAV_ITEMS, role).filter((item) => !primaryIds.has(item.id));
}

export function isMobileMoreView(viewId: string, role?: string | null): boolean {
  return mobileMoreItemsForRole(role).some((item) => item.id === viewId);
}

export function isProjectRequiredView(viewId: string): boolean {
  return PROJECT_REQUIRED_VIEW_IDS.has(viewId as ViewId);
}

export function isKnownView(viewId: string): viewId is ViewId {
  return ALL_NAV_ITEMS.some((item) => item.id === viewId);
}
