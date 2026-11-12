import "server-only";
import createClient from "openapi-fetch";
import { headers } from "next/headers";
import { notFound, redirect } from "next/navigation";
import type { paths } from "@/lib/api-client/schema";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8010";

/** Typed API client for server components. Forwards the session cookie that proxy.ts verified. */
export async function serverApi() {
  const cookie = (await headers()).get("cookie") ?? "";
  return createClient<paths>({ baseUrl: BACKEND, headers: { cookie }, cache: "no-store" });
}

/** Unwrap a response: 404 renders the not-found page, 401 goes to sign-in, anything else throws. */
export function unwrap<T>(res: { data?: T; response: Response }): T {
  if (res.data !== undefined) return res.data;
  if (res.response.status === 404) notFound();
  if (res.response.status === 401) redirect("/login");
  throw new Error(`API request failed (${res.response.status})`);
}
