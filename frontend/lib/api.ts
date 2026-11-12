import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "@/lib/api-client/schema";

/**
 * Typed client for browser use. Paths already include /api/v1; cookies are sent automatically.
 *
 * The access token lives 15 minutes. When a call comes back 401 we try the refresh cookie once
 * (shared between concurrent calls), retry the original request, and only then send the user
 * back to sign in.
 */
let refreshing: Promise<boolean> | null = null;
const originals = new WeakMap<Request, Request>();

function refreshSession(): Promise<boolean> {
  refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST", credentials: "same-origin" })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

const retryOn401: Middleware = {
  onRequest({ request }) {
    originals.set(request, request.clone()); // a body can only be read once, so keep a spare
    return request;
  },
  async onResponse({ request, response }) {
    const path = new URL(request.url).pathname;
    if (response.status !== 401 || path.startsWith("/api/v1/auth/")) return response;
    const spare = originals.get(request);
    if (spare && (await refreshSession())) return fetch(spare);
    if (typeof window !== "undefined") {
      // Deliberate full-page navigation: drops all client state for the signed-out session.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });
api.use(retryOn401);

/** Pull a readable message out of an API error body. */
export function errorMessage(err: unknown, fallback = "Something went wrong. Please try again."): string {
  const detail = (err as { detail?: unknown } | undefined)?.detail;
  return typeof detail === "string" ? detail : fallback;
}
