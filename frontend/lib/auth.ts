import type { components } from "@/lib/api-client/schema";

export type User = components["schemas"]["UserOut"];
export type Role = User["role"];

/** Where each role lands after sign-in. */
export const HOME: Record<Role, string> = {
  student: "/student",
  faculty: "/faculty",
  admin: "/admin",
};

export const homeFor = (role: Role) => HOME[role];

/** Which role owns each top-level area. */
export const AREA_ROLE: Record<string, Role> = {
  student: "student",
  faculty: "faculty",
  admin: "admin",
};

/** Only allow same-site relative redirects, and only into the user's own area. */
export function safeRedirect(target: string | null | undefined, role: Role): string {
  if (!target || !target.startsWith("/") || target.startsWith("//")) return homeFor(role);
  const area = target.split("/")[1]?.split("?")[0];
  return AREA_ROLE[area] === role ? target : homeFor(role);
}

export const USER_HEADER = "x-gradient-user";
