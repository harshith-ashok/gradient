"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { useToast } from "./Toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Settings = components["schemas"]["SettingsOut"];
type Row = Settings["courses"][number] & { useOverride: boolean; value: number };

const toRows = (s: Settings): Row[] =>
  s.courses.map((c) => ({ ...c, useOverride: c.override !== null, value: c.override ?? s.global_threshold }));

export function SettingsForm({ initial }: { initial: Settings }) {
  const router = useRouter();
  const toast = useToast();
  const [saved, setSaved] = useState(initial);
  const [globalT, setGlobalT] = useState(initial.global_threshold);
  const [rows, setRows] = useState<Row[]>(() => toRows(initial));
  const [saving, setSaving] = useState(false);

  const payload = (g: number, rs: Row[]) =>
    JSON.stringify([g, rs.map((r) => [r.id, r.useOverride ? r.value : null])]);
  const dirty = useMemo(
    () => payload(globalT, rows) !== payload(saved.global_threshold, toRows(saved)),
    [globalT, rows, saved],
  );
  const { min, max } = saved;
  const invalid = (n: number) => !Number.isInteger(n) || n < min || n > max;
  const hasError = invalid(globalT) || rows.some((r) => r.useOverride && invalid(r.value));
  const patch = (id: string, change: Partial<Row>) => setRows(rows.map((r) => (r.id === id ? { ...r, ...change } : r)));

  async function save() {
    setSaving(true);
    const per_course = Object.fromEntries(rows.filter((r) => r.useOverride).map((r) => [r.id, r.value]));
    const { data, error } = await api.PUT("/api/v1/admin/settings", { body: { global_threshold: globalT, per_course } });
    setSaving(false);
    if (error || !data) return toast(errorMessage(error), "error");
    setSaved(data);
    setGlobalT(data.global_threshold);
    setRows(toRows(data));
    toast("Pass mark settings saved. They apply to every quiz from now on.", "success");
    router.refresh();
  }

  return (
    <div className="max-w-[860px] space-y-5">
      <Card className="gap-0 p-6">
        <h2 className="text-xl font-semibold">Global pass mark</h2>
        <p className="text-sm text-muted-foreground">Used for every course that does not have its own setting.</p>
        <div className="mt-3 flex items-center gap-6">
          <div className="w-28  text-5xl tabular-nums">{globalT}%</div>
          <div className="flex-1">
            <label className="sr-only" htmlFor="g">Global pass mark</label>
            <input
              id="g" type="range" min={min} max={max} step={5} value={globalT}
              onChange={(e) => setGlobalT(Number(e.target.value))} className="w-full accent-[var(--primary)]"
            />
            <div className="flex justify-between text-xs text-muted-foreground"><span>{min}%</span><span>{max}%</span></div>
          </div>
        </div>
      </Card>

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h2 className="text-xl font-semibold">Per-course overrides</h2></div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Course</TableHead><TableHead>Status</TableHead><TableHead>Override</TableHead><TableHead className="w-36">Pass mark</TableHead><TableHead className="text-right tabular-nums">Applies</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell><b>{r.code}</b> · {r.title}</TableCell>
                  <TableCell><Badge variant={r.status === "published" ? "success" : "warning"}>{r.status === "published" ? "Published" : "Draft"}</Badge></TableCell>
                  <TableCell>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox" checked={r.useOverride} aria-label={`Override pass mark for ${r.title}`}
                        onChange={(e) => patch(r.id, { useOverride: e.target.checked })}
                      />
                      Use own pass mark
                    </label>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Input type="number" min={min} max={max} step={5} value={r.value} disabled={!r.useOverride} aria-label={`Pass mark for ${r.title}`} aria-invalid={r.useOverride && invalid(r.value)} onChange={(e) => patch(r.id, { value: Number(e.target.value) })} className="disabled:opacity-50 aria-[invalid=true]:border-destructive" />
                      <span className="text-muted-foreground">%</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums"><b>{r.useOverride ? r.value : globalT}%</b></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <div className="flex items-center gap-3">
        <Button type="button" disabled={!dirty || saving || hasError} onClick={save} size="lg">
          {saving ? "Saving…" : "Save settings"}
        </Button>
        {dirty && <Badge variant="warning">Unsaved changes</Badge>}
        {hasError && <span className="text-sm text-destructive">Pass marks must be whole numbers from {min} to {max}.</span>}
      </div>
    </div>
  );
}
