"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";
import { LEVEL_TONE, statusTone } from "./ui";

type Log = components["schemas"]["LogOut"];
const PAGE_SIZE = 50;

export function LogViewer({ initialRequestId }: { initialRequestId: string }) {
  const [f, setF] = useState({ level: "", kind: "", q: "", path: "", request_id: initialRequestId, min_status: "", source: "", minutes: "60" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: Log[]; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    const query = {
      level: (f.level || undefined) as "INFO" | undefined,
      kind: (f.kind || undefined) as "requests" | undefined,
      q: f.q, path: f.path, request_id: f.request_id,
      min_status: f.min_status ? Number(f.min_status) : undefined,
      source: (f.source || undefined) as "api" | undefined,
      minutes: f.minutes ? Number(f.minutes) : undefined,
      page, page_size: PAGE_SIZE,
    };
    const { data, error } = await api.GET("/api/v1/admin/logs", { params: { query } });
    if (error || !data) return setError(errorMessage(error));
    setError(null);
    setData(data);
  }, [f, page]);

  useEffect(() => {
    const t = setTimeout(load, 250); // wait for the person to stop typing
    return () => clearTimeout(t);
  }, [load]);
  useEffect(() => {
    if (!live) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [live, load]);

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setF({ ...f, [k]: e.target.value });
    setPage(1);
  };
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="card">
      <div className="flex flex-wrap items-center gap-3 border-b border-line-soft p-4">
        <input value={f.q} onChange={set("q")} className="input !w-56" placeholder="Search messages" aria-label="Search messages" />
        <input value={f.path} onChange={set("path")} className="input !w-44" placeholder="Path contains…" aria-label="Path contains" />
        <input value={f.request_id} onChange={set("request_id")} className="input !w-56" placeholder="Request ID" aria-label="Request ID" />
        <select value={f.level} onChange={set("level")} className="input !w-auto" aria-label="Minimum level">
          <option value="">All levels</option>
          <option value="WARNING">Warnings and above</option>
          <option value="ERROR">Errors only</option>
        </select>
        <select value={f.kind} onChange={set("kind")} className="input !w-auto" aria-label="Kind">
          <option value="">Requests and events</option>
          <option value="requests">Requests only</option>
          <option value="events">Events only</option>
        </select>
        <select value={f.min_status} onChange={set("min_status")} className="input !w-auto" aria-label="Status">
          <option value="">Any status</option>
          <option value="400">4xx and 5xx</option>
          <option value="500">5xx only</option>
        </select>
        <select value={f.source} onChange={set("source")} className="input !w-auto" aria-label="Source">
          <option value="">API and worker</option>
          <option value="api">API</option>
          <option value="worker">AI worker</option>
        </select>
        <select value={f.minutes} onChange={set("minutes")} className="input !w-auto" aria-label="Time range">
          <option value="15">Last 15 minutes</option>
          <option value="60">Last hour</option>
          <option value="1440">Last 24 hours</option>
          <option value="10080">Last 7 days</option>
          <option value="">Everything kept</option>
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} /> Live (every 5 s)
        </label>
        <span className="ml-auto text-sm text-muted">{data ? `${data.total} ${data.total === 1 ? "entry" : "entries"}` : "Loading…"}</span>
      </div>
      {error && <p role="alert" className="border-b border-line-soft p-4 text-sm text-bad">{error}</p>}
      <div className="overflow-x-auto">
        <table className="table">
          <thead><tr><th>Time (UTC)</th><th>Level</th><th>What happened</th><th>Who</th><th className="num">ms</th></tr></thead>
          <tbody>
            {data?.items.map((l) => (
              <LogRow key={l.id} l={l} open={open === l.id} toggle={() => setOpen(open === l.id ? null : l.id)}
                filterRequest={() => { setF({ ...f, request_id: l.request_id ?? "" }); setPage(1); }} />
            ))}
            {data && !data.items.length && <tr><td colSpan={5} className="empty">Nothing logged for these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <nav aria-label="Pagination" className="flex items-center justify-between border-t border-line-soft px-4 py-3 text-sm">
          <button type="button" className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Newer</button>
          <span className="text-muted">Page {page} of {pages}</span>
          <button type="button" className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Older →</button>
        </nav>
      )}
    </div>
  );
}

function LogRow({ l, open, toggle, filterRequest }: { l: Log; open: boolean; toggle: () => void; filterRequest: () => void }) {
  return (
    <>
      <tr className="cursor-pointer hover:bg-ink-50" onClick={toggle}>
        <td className="whitespace-nowrap text-sm text-muted">{fmtUtc(l.ts)}</td>
        <td><span className={`badge ${LEVEL_TONE[l.level]}`}>{l.level}</span></td>
        <td>
          {l.method ? (
            <>
              <span className={`badge ${statusTone(l.status)} mr-2`}>{l.status}</span>
              <b>{l.method}</b> <code className="text-[13px]">{l.path}</code>
            </>
          ) : (
            <span>{l.message}</span>
          )}
          <div className="text-xs text-muted">{l.logger} · {l.source}</div>
        </td>
        <td className="text-sm">{l.user_name ?? (l.user_id ? l.user_id : <span className="text-muted">anonymous</span>)}{l.role && <span className="text-muted"> · {l.role}</span>}</td>
        <td className="num">{l.duration_ms ?? ""}</td>
      </tr>
      {open && (
        <tr className="bg-ink-50">
          <td colSpan={5} className="text-sm">
            <p className="whitespace-pre-wrap break-words">{l.message}</p>
            {l.request_id && (
              <p className="mt-2 flex flex-wrap items-center gap-3">
                <span>Request ID <code>{l.request_id}</code></span>
                <button type="button" className="btn btn-secondary btn-sm" onClick={filterRequest}>Show this request only</button>
                {l.status && l.status >= 500 && (
                  <Link href="/admin/issues" className="text-crimson hover:underline">See issues</Link>
                )}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
