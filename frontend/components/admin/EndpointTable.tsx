"use client";

import { useMemo, useState } from "react";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge, type BadgeTone } from "@/components/ui/badge";

type Endpoint = components["schemas"]["EndpointInfo"];
const METHOD_TONE: Record<string, BadgeTone> = { GET: "secondary", POST: "success", PUT: "warning", DELETE: "destructive" };
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
    <Card className="gap-0 py-0">
      <div className="flex flex-wrap items-center gap-3 border-b border-border p-4">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search path or name" aria-label="Search endpoints" className="!w-72" />
        <NativeSelect value={group} onChange={(e) => setGroup(e.target.value)} aria-label="Group" className="!w-auto">
          <option value="">All groups</option>
          {groups.map((g) => <option key={g} value={g}>{g}</option>)}
        </NativeSelect>
        <NativeSelect value={role} onChange={(e) => setRole(e.target.value)} aria-label="Can be called by" className="!w-auto">
          <option value="">Anyone</option>
          <option value="public">Public (no sign-in)</option>
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="admin">Admin</option>
        </NativeSelect>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyErrors} onChange={(e) => setOnlyErrors(e.target.checked)} /> Only with errors
        </label>
        <span className="ml-auto text-sm text-muted-foreground">{shown.length} of {endpoints.length}</span>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Endpoint</TableHead><TableHead>Who can call it</TableHead><TableHead className="text-right tabular-nums">Calls</TableHead><TableHead className="text-right tabular-nums">4xx</TableHead>
              <TableHead className="text-right tabular-nums">5xx</TableHead><TableHead className="text-right tabular-nums">Avg ms</TableHead><TableHead className="text-right tabular-nums">Slowest</TableHead><TableHead>Last call (UTC)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((e) => (
              <TableRow key={e.method + e.path}>
                <TableCell>
                  <Badge variant={METHOD_TONE[e.method] ?? "secondary"} className="mr-2">{e.method}</Badge>
                  <code className="text-[13px]">{e.path}</code>
                  <div className="text-xs text-muted-foreground">{e.group} · {e.summary}</div>
                </TableCell>
                <TableCell>
                  {e.access === "roles" ? (
                    <div className="flex gap-1">{e.roles.map((r) => <Badge key={r} variant="default">{r}</Badge>)}</div>
                  ) : (
                    <Badge variant={e.access === "public" ? "warning" : "secondary"}>{ACCESS_LABEL[e.access]}</Badge>
                  )}
                </TableCell>
                <TableCell className="text-right tabular-nums">{e.stats.requests ?? 0}</TableCell>
                <TableCell className={`num ${e.stats.client_errors ? "text-warning" : ""}`}>{e.stats.client_errors ?? 0}</TableCell>
                <TableCell className={`num ${e.stats.server_errors ? "font-bold text-destructive" : ""}`}>{e.stats.server_errors ?? 0}</TableCell>
                <TableCell className="text-right tabular-nums">{e.stats.requests ? e.stats.avg_ms : "–"}</TableCell>
                <TableCell className="text-right tabular-nums">{e.stats.requests ? e.stats.max_ms : "–"}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{e.stats.last_called ? fmtUtc(e.stats.last_called) : "–"}</TableCell>
              </TableRow>
            ))}
            {!shown.length && <TableRow><TableCell colSpan={8} className="empty">No endpoints match.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
