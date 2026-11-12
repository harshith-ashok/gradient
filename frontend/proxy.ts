import { NextResponse, type NextRequest } from "next/server";
import { AREA_ROLE, USER_HEADER, homeFor, type User } from "@/lib/auth";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8010";

async function fetchMe(cookie: string): Promise<User | null> {
  if (!cookie) return null;
  const r = await fetch(`${BACKEND}/api/v1/auth/me`, { headers: { cookie }, cache: "no-store" });
  return r.ok ? ((await r.json()) as User) : null;
}

/** Access token expired but a refresh cookie exists: get a new pair and use it for this request. */
async function refresh(cookie: string) {
  const r = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { cookie },
    cache: "no-store",
  });
  if (!r.ok) return null;
  const setCookies = r.headers.getSetCookie();
  const fresh = new Map<string, string>();
  for (const c of setCookies) {
    const [pair] = c.split(";");
    const i = pair.indexOf("=");
    fresh.set(pair.slice(0, i), pair.slice(i + 1));
  }
  const merged = new Map<string, string>();
  for (const part of cookie.split(/;\s*/)) {
    const i = part.indexOf("=");
    if (i > 0) merged.set(part.slice(0, i), part.slice(i + 1));
  }
  fresh.forEach((v, k) => merged.set(k, v));
  const cookieHeader = [...merged].map(([k, v]) => `${k}=${v}`).join("; ");
  return { user: (await r.json()) as User, setCookies, cookieHeader };
}

export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  let cookie = request.headers.get("cookie") ?? "";
  let setCookies: string[] = [];

  let user = await fetchMe(cookie);
  if (!user && request.cookies.has("refresh_token")) {
    const renewed = await refresh(cookie);
    if (renewed) {
      user = renewed.user;
      setCookies = renewed.setCookies;
      cookie = renewed.cookieHeader;
    }
  }

  const finish = (res: NextResponse) => {
    setCookies.forEach((c) => res.headers.append("set-cookie", c));
    return res;
  };
  const redirect = (to: string) => finish(NextResponse.redirect(new URL(to, request.url)));

  const area = pathname.split("/")[1];

  if (pathname === "/") return redirect(user ? homeFor(user.role) : "/login");
  if (pathname === "/login") {
    return user ? redirect(homeFor(user.role)) : finish(NextResponse.next());
  }
  if (area in AREA_ROLE) {
    if (!user) return redirect(`/login?redirect=${encodeURIComponent(pathname + search)}`);
    if (AREA_ROLE[area] !== user.role) return redirect(homeFor(user.role));
  }

  // Hand the verified user to server components. Always overwrite so a client can't spoof it.
  const headers = new Headers(request.headers);
  headers.delete(USER_HEADER);
  if (user) headers.set(USER_HEADER, encodeURIComponent(JSON.stringify(user)));
  headers.set("cookie", cookie);
  return finish(NextResponse.next({ request: { headers } }));
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
