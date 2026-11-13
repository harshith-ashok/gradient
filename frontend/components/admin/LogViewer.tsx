"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";
import { LEVEL_TONE, statusTone } from "./ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
    <Card className="gap-0 py-0">
      <div className="flex flex-wrap items-center gap-3 border-b border-border p-4">
        <Input value={f.q} onChange={set("q")} placeholder="Search messages" aria-label="Search messages" className="!w-56" />
        <Input value={f.path} onChange={set("path")} placeholder="Path contains…" aria-label="Path contains" className="!w-44" />
        <Input value={f.request_id} onChange={set("request_id")} placeholder="Request ID" aria-label="Request ID" className="!w-56" />
        <NativeSelect value={f.level} onChange={set("level")} aria-label="Minimum level" className="!w-auto">
          <option value="">All levels</option>
          <option value="WARNING">Warnings and above</option>
          <option value="ERROR">Errors only</option>
        </NativeSelect>
        <NativeSelect value={f.kind} onChange={set("kind")} aria-label="Kind" className="!w-auto">
          <option value="">Requests and events</option>
          <option value="requests">Requests only</option>
          <option value="events">Events only</option>
        </NativeSelect>
        <NativeSelect value={f.min_status} onChange={set("min_status")} aria-label="Status" className="!w-auto">
          <option value="">Any status</option>
          <option value="400">4xx and 5xx</option>
          <option value="500">5xx only</option>
        </NativeSelect>
        <NativeSelect value={f.source} onChange={set("source")} aria-label="Source" className="!w-auto">
          <option value="">API and worker</option>
          <option value="api">API</option>
          <option value="worker">AI worker</option>
          <option value="judge">Code runner</option>
        </NativeSelect>
        <NativeSelect value={f.minutes} onChange={set("minutes")} aria-label="Time range" className="!w-auto">
          <option value="15">Last 15 minutes</option>
          <option value="60">Last hour</option>
          <option value="1440">Last 24 hours</option>
          <option value="10080">Last 7 days</option>
          <option value="">Everything kept</option>
        </NativeSelect>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} /> Live (every 5 s)
        </label>
        <span className="ml-auto text-sm text-muted-foreground">{data ? `${data.total} ${data.total === 1 ? "entry" : "entries"}` : "Loading…"}</span>
      </div>
      {error && <p role="alert" className="border-b border-border p-4 text-sm text-destructive">{error}</p>}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow><TableHead>Time (UTC)</TableHead><TableHead>Level</TableHead><TableHead>What happened</TableHead><TableHead>Who</TableHead><TableHead className="text-right tabular-nums">ms</TableHead></TableRow></TableHeader>
          <TableBody>
            {data?.items.map((l) => (
              <LogRow key={l.id} l={l} open={open === l.id} toggle={() => setOpen(open === l.id ? null : l.id)}
                filterRequest={() => { setF({ ...f, request_id: l.request_id ?? "" }); setPage(1); }} />
            ))}
            {data && !data.items.length && <TableRow><TableCell colSpan={5} className="empty">Nothing logged for these filters.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
      {pages > 1 && (
        <nav aria-label="Pagination" className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
          <Button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} variant="outline" size="sm">← Newer</Button>
          <span className="text-muted-foreground">Page {page} of {pages}</span>
          <Button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)} variant="outline" size="sm">Older →</Button>
        </nav>
      )}
    </Card>
  );
}

function LogRow({ l, open, toggle, filterRequest }: { l: Log; open: boolean; toggle: () => void; filterRequest: () => void }) {
  return (
    <>
      <TableRow onClick={toggle} className="cursor-pointer hover:bg-muted">
        <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{fmtUtc(l.ts)}</TableCell>
        <TableCell><Badge variant={LEVEL_TONE[l.level]}>{l.level}</Badge></TableCell>
        <TableCell>
          {l.method ? (
            <>
              <Badge variant={statusTone(l.status)} className="mr-2">{l.status}</Badge>
              <b>{l.method}</b> <code className="text-[13px]">{l.path}</code>
            </>
          ) : (
            <span>{l.message}</span>
          )}
          <div className="text-xs text-muted-foreground">{l.logger} · {l.source}</div>
        </TableCell>
        <TableCell className="text-sm">{l.user_name ?? (l.user_id ? l.user_id : <span className="text-muted-foreground">anonymous</span>)}{l.role && <span className="text-muted-foreground"> · {l.role}</span>}</TableCell>
        <TableCell className="text-right tabular-nums">{l.duration_ms ?? ""}</TableCell>
      </TableRow>
      {open && (
        <TableRow className="bg-muted">
          <TableCell colSpan={5} className="text-sm">
            <p className="whitespace-pre-wrap break-words">{l.message}</p>
            {l.request_id && (
              <p className="mt-2 flex flex-wrap items-center gap-3">
                <span>Request ID <code>{l.request_id}</code></span>
                <Button type="button" onClick={filterRequest} variant="outline" size="sm">Show this request only</Button>
                {l.status && l.status >= 500 && (
                  <Link href="/admin/issues" className="text-primary hover:underline">See issues</Link>
                )}
              </p>
            )}
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
