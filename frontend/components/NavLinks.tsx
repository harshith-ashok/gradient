"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Role } from "@/lib/auth";

const NAV: Record<Role, { to: string; label: string; exact?: boolean }[]> = {
  student: [
    { to: "/student", label: "Dashboard", exact: true },
    { to: "/student/courses", label: "Courses" },
    { to: "/student/practice", label: "Practice" },
    { to: "/student/progress", label: "Progress" },
  ],
  faculty: [
    { to: "/faculty", label: "My courses", exact: true },
    { to: "/faculty/new", label: "New course" },
  ],
  admin: [
    { to: "/admin", label: "Students", exact: true },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/access", label: "Roles & endpoints" },
    { to: "/admin/logs", label: "Logs" },
    { to: "/admin/issues", label: "Issues" },
    { to: "/admin/system", label: "System" },
    { to: "/admin/settings", label: "Pass mark" },
  ],
};

export function NavLinks({ role }: { role: Role }) {
  const path = usePathname();
  return (
    <nav aria-label="Primary" className="flex flex-1 gap-1 text-sm">
      {NAV[role].map((l) => {
        const active = l.exact ? path === l.to : path.startsWith(l.to);
        return (
          <Link
            key={l.to}
            href={l.to}
            aria-current={active ? "page" : undefined}
            className="rounded-sm px-3 py-1.5 font-medium text-muted hover:text-ink-900 aria-[current=page]:text-crimson"
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
