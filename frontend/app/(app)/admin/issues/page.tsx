import type { Metadata } from "next";
import Link from "next/link";
import { Pager, Stat, one, qs } from "@/components/admin/ui";
import { PageHeader } from "@/components/PageHeader";
import { fmtUtc } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const metadata: Metadata = { title: "Issues" };
const STATUSES = ["open", "resolved", "ignored"] as const;
const TONE = { open: "destructive", resolved: "success", ignored: "secondary" } as const;
const PAGE_SIZE = 15;

export default async function IssuesPage({ searchParams }: PageProps<"/admin/issues">) {
  const sp = await searchParams;
  const q = one(sp.q) ?? "";
  const status = STATUSES.find((s) => s === one(sp.status)) ?? (one(sp.status) === "all" ? undefined : "open");
  const page = Math.max(1, Number(one(sp.page)) || 1);

  const api = await serverApi();
  const data = unwrap(await api.GET("/api/v1/admin/issues", { params: { query: { status, q, page, page_size: PAGE_SIZE } } }));
  const href = (p: number) => `/admin/issues${qs({ q, status: status ?? "all", page: p })}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "Issues" }]}
        eyebrow="Management"
        title="Issues"
        lede="Unhandled errors, grouped by where they happen so one bug is one row however often it fires. Each has its stack trace and the requests that hit it. A resolved issue reopens by itself if it comes back."
      />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Stat value={data.by_status.open ?? 0} label="Open" tone={data.by_status.open ? "bad" : undefined} />
        <Stat value={data.by_status.resolved ?? 0} label="Resolved" />
        <Stat value={data.by_status.ignored ?? 0} label="Ignored" />
      </div>
      <Card className="gap-0 py-0">
        <form method="get" className="flex flex-wrap items-center gap-3 border-b border-border p-4">
          <label className="sr-only" htmlFor="q">Search issues</label>
          <Input id="q" name="q" defaultValue={q} placeholder="Search error or file" className="!w-72" />
          <label className="sr-only" htmlFor="status">Status</label>
          <NativeSelect id="status" name="status" defaultValue={status ?? "all"} className="!w-auto">
            <option value="all">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </NativeSelect>
          <Button type="submit" size="sm">Apply</Button>
          <span className="ml-auto text-sm text-muted-foreground">{data.total} {data.total === 1 ? "issue" : "issues"}</span>
        </form>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Error</TableHead><TableHead>Status</TableHead><TableHead className="text-right tabular-nums">Times</TableHead><TableHead>First seen (UTC)</TableHead><TableHead>Last seen (UTC)</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((i) => (
                <TableRow key={i.id} className="hover:bg-muted">
                  <TableCell className="max-w-[520px]">
                    <Link href={`/admin/issues/${i.id}`} className="font-semibold hover:text-primary hover:underline">{i.title}</Link>
                    <div className="text-xs text-muted-foreground">{i.culprit} · {i.source}</div>
                  </TableCell>
                  <TableCell><Badge variant={TONE[i.status]}>{i.status}</Badge></TableCell>
                  <TableCell className="text-right tabular-nums">{i.count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{fmtUtc(i.first_seen)}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{fmtUtc(i.last_seen)}</TableCell>
                </TableRow>
              ))}
              {!data.items.length && (
                <TableRow><TableCell colSpan={5} className="empty"><h3>No issues here</h3>{status === "open" ? "Nothing is currently failing." : "Nothing matches these filters."}</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <Pager page={page} size={PAGE_SIZE} total={data.total} href={href} />
      </Card>
    </>
  );
}
