"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { safeRedirect } from "@/lib/auth";
import type { components } from "@/lib/api-client/schema";

type Portal = "student" | "staff";
type Demo = components["schemas"]["DemoLogin"];

const PORTALS: { id: Portal; label: string }[] = [
  { id: "student", label: "Student" },
  { id: "staff", label: "Faculty / Management" },
];

export function LoginForm({ redirectTo }: { redirectTo: string | null }) {
  const router = useRouter();
  const [portal, setPortal] = useState<Portal>("student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [demos, setDemos] = useState<Demo[]>([]);

  useEffect(() => {
    api.GET("/api/v1/auth/demo-logins").then(({ data }) => data && setDemos(data));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const { data, error: err } = await api.POST("/api/v1/auth/login", {
      body: { email, password, portal },
    });
    if (data) {
      router.replace(safeRedirect(redirectTo, data.role));
      router.refresh();
      return;
    }
    setBusy(false);
    const detail = (err as { detail?: unknown } | undefined)?.detail;
    setError(typeof detail === "string" ? detail : "Could not sign in. Check your details and try again.");
  }

  const input =
    "w-full rounded-sm border border-line bg-surface px-3 py-2.5 text-ink placeholder:text-faint";

  return (
    <div className="w-full max-w-[420px]">
      <h2 className="text-3xl font-semibold">Welcome back</h2>
      <p className="mt-1 text-muted">Choose your portal and sign in with your university credentials.</p>

      <div role="group" aria-label="Portal" className="mb-6 mt-5 grid grid-cols-2 rounded-md bg-ink-100 p-1">
        {PORTALS.map((p) => (
          <button
            key={p.id}
            type="button"
            aria-pressed={portal === p.id}
            onClick={() => {
              setPortal(p.id);
              setError("");
            }}
            className="rounded-sm px-3 py-2 text-sm font-medium text-muted transition-colors aria-pressed:bg-surface aria-pressed:text-ink-900 aria-pressed:shadow-sm"
          >
            {p.label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} noValidate className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium">University email</label>
          <input
            id="email" type="email" autoComplete="username" required value={email}
            onChange={(e) => setEmail(e.target.value)} placeholder="name@gradient.edu" className={input}
          />
        </div>
        <div>
          <label htmlFor="pw" className="mb-1.5 block text-sm font-medium">Password</label>
          <div className="flex gap-2">
            <input
              id="pw" type={show ? "text" : "password"} autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} className={input}
            />
            <button
              type="button" aria-pressed={show} onClick={() => setShow(!show)}
              className="rounded-sm border border-line px-3 text-sm text-ink-700 hover:bg-ink-50"
            >
              {show ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        {error && (
          <div role="alert" className="rounded-sm bg-bad-bg px-3 py-2.5 text-sm text-bad">{error}</div>
        )}
        <button
          type="submit" disabled={busy || !email || !password}
          className="w-full rounded-sm bg-ink-900 px-4 py-3 font-medium text-white transition-colors hover:bg-ink-700 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {demos.length > 0 && (
        <div className="mt-8 rounded-md border border-line-soft bg-ink-50 p-4">
          <h3 className="font-sans text-xs font-semibold uppercase tracking-wider text-muted">Demo accounts</h3>
          <div className="mt-2 divide-y divide-line-soft">
            {demos.filter((d) => d.portal === portal).map((d) => (
              <button
                key={d.email} type="button"
                onClick={() => { setEmail(d.email); setPassword(d.password); setError(""); }}
                className="flex w-full items-center justify-between py-2.5 text-left hover:text-crimson"
              >
                <span>
                  <b className="block text-sm font-medium">{d.name}</b>
                  <small className="text-xs text-muted">{d.note}</small>
                </span>
                <small className="text-xs text-faint">Use</small>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
