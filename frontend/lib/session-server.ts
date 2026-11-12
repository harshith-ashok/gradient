import "server-only";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { USER_HEADER, type User } from "@/lib/auth";

/** The signed-in user, as verified and forwarded by proxy.ts. */
export async function currentUser(): Promise<User> {
  const raw = (await headers()).get(USER_HEADER);
  if (!raw) redirect("/login");
  return JSON.parse(decodeURIComponent(raw)) as User;
}
