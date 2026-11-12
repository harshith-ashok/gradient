"use client";

import { useMemo, useState } from "react";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";

type Endpoint = components["schemas"]["EndpointInfo"];
const METHOD_TONE: Record<string, string> = { GET: "badge-info", POST: "badge-ok", PUT: "badge-warn", DELETE: "badge-bad" };
const ACCESS_LABEL = { public: "Public", "signed-in": "Any signed-in user", roles: "By role" } as const;

export function EndpointTable({ endpoints }: { endpoints: Endpoint[] }) {
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [group, setGroup] = useState("");
  const [onlyErrors, setOnlyErrors] = useState(false);

  const groups = useMemo(() => [...new Set(endpoints.map((e) => e.group))], [endpoints]);
  const shown = endpoints.filter(
    (e) =>
      (!q || `${e.method} ${e.path} ${e.summary}`.toLowerCase().includes(q.toLowerCase())) &&
      (!group || e.group === group) &&
      (!role || (role === "public" ? e.access === "public" : e.access !== "public" && e.roles.includes(role as never))) &&
      (!onlyErrors || e.stats.server_errors + e.stats.client_errors > 0),
  );

  return (
    <div className="card">
      <div className="flex flex-wrap items-center gap-3 border-b border-line-soft p-4">
        <input value={q} onChange={(e) => setQ(e.target.value)} className="input !w-72" placeholder="Search path or name" aria-label="Search endpoints" />
        <select value={group} onChange={(e) => setGroup(e.target.value)} className="input !w-auto" aria-label="Group">
          <option value="">All groups</option>
          {groups.map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
        <select value={role} onChange={(e) => setRole(e.target.value)} className="input !w-auto" aria-label="Can be called by">
          <option value="">Anyone</option>
          <option value="public">Public (no sign-in)</option>
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="admin">Admin</option>
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyErrors} onChange={(e) => setOnlyErrors(e.target.checked)} /> Only with errors
        </label>
        <span className="ml-auto text-sm text-muted">{shown.length} of {endpoints.length}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Endpoint</th><th>Who can call it</th><th className="num">Calls</th><th className="num">4xx</th>
              <th className="num">5xx</th><th className="num">Avg ms</th><th className="num">Slowest</th><th>Last call (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.method + e.path}>
                <td>
                  <span className={`badge ${METHOD_TONE[e.method] ?? "badge-info"} mr-2`}>{e.method}</span>
                  <code className="text-[13px]">{e.path}</code>
                  <div className="text-xs text-muted">{e.group} · {e.summary}</div>
                </td>
                <td>
                  {e.access === "roles" ? (
                    <div className="flex gap-1">{e.roles.map((r) => <span key={r} className="badge badge-crimson">{r}</span>)}</div>
                  ) : (
                    <span className={`badge ${e.access === "public" ? "badge-warn" : "badge-info"}`}>{ACCESS_LABEL[e.access]}</span>
                  )}
                </td>
                <td className="num">{e.stats.requests ?? 0}</td>
                <td className={`num ${e.stats.client_errors ? "text-warn" : ""}`}>{e.stats.client_errors ?? 0}</td>
                <td className={`num ${e.stats.server_errors ? "font-bold text-bad" : ""}`}>{e.stats.server_errors ?? 0}</td>
                <td className="num">{e.stats.requests ? e.stats.avg_ms : "–"}</td>
                <td className="num">{e.stats.requests ? e.stats.max_ms : "–"}</td>
                <td className="text-sm text-muted">{e.stats.last_called ? fmtUtc(e.stats.last_called) : "–"}</td>
              </tr>
            ))}
            {!shown.length && <tr><td colSpan={8} className="empty">No endpoints match.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
