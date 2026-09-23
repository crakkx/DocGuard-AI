import {
  LayoutDashboard,
  FileText,
  Briefcase,
  ScrollText,
  ShieldCheck,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/cases", label: "Cases", icon: Briefcase },
  { href: "/policies", label: "Policies", icon: ScrollText },
  { href: "/rules", label: "Rules", icon: ShieldCheck },
] as const;

