import type { Metadata } from "next";
import Link from "next/link";
import { ModelCheck } from "@/components/admin/ModelCheck";
import { Stat } from "@/components/admin/ui";
import { PageHeader } from "@/components/PageHeader";
import { fmtUtc } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "System" };
export const dynamic = "force-dynamic";

export default async function SystemPage() {
  const api = await serverApi();
  const s = unwrap(await api.GET("/api/v1/admin/system"));
  const peak = Math.max(1, ...s.traffic.map((t) => t.requests));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "System" }]}
        eyebrow="Management"
        title="System"
        lede="Are the services up, is the AI worker keeping up, and how has the API behaved over the last day."
        actions={<Link href="/admin/system" className={buttonVariants({ variant: "outline" })}>Refresh</Link>}
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={s.requests_24h} label="API requests, 24 h" />
        <Stat value={s.server_errors_24h} label="Server errors (5xx), 24 h" tone={s.server_errors_24h ? "bad" : undefined} />
        <Stat value={`${s.avg_ms_24h} ms`} label="Average response time" />
        <Stat value={s.open_issues} label="Open issues" tone={s.open_issues ? "bad" : undefined} />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card className="gap-0 p-6">
          <h2 className="mb-3 text-xl font-semibold">Services</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(s.checks).map(([name, state]) => (
              <li key={name} className="flex items-center justify-between">
                <span className="capitalize">{name}</span>
                <Badge variant={state === "ok" ? "success" : "destructive"}>{state === "ok" ? "Up" : "Down"}</Badge>
              </li>
            ))}
            <li className="flex items-center justify-between">
              <span>Model server ({s.llm_provider} · {s.llm_model})</span>
              <ModelCheck />
            </li>
          </ul>
          <p className="mt-4 text-xs text-muted-foreground">
            Environment <b>{s.environment}</b> · logs kept {s.log_retention_days} days · {s.log_rows} rows stored
          </p>
        </Card>
        <Card className="gap-0 p-6">
          <h2 className="mb-3 text-xl font-semibold">AI worker queue</h2>
          <dl className="grid grid-cols-4 gap-3 text-center">
            {(["queued", "running", "succeeded", "failed"] as const).map((k) => (
              <div key={k}>
                <dt className="text-xs capitalize text-muted-foreground">{k}</dt>
                <dd className={` text-3xl tabular-nums ${k === "failed" && s.jobs[k] ? "text-destructive" : ""}`}>{s.jobs[k]}</dd>
              </div>
            ))}
          </dl>
          {s.jobs.queued > 0 && s.jobs.running === 0 && (
            <p role="alert" className="mt-3 text-sm text-warning">Jobs are waiting but none is running. Is the worker started?</p>
          )}
        </Card>
      </div>

      <Card className="gap-0 p-6 mb-6">
        <h2 className="mb-1 text-xl font-semibold">Traffic, last 24 hours</h2>
        <p className="mb-4 text-sm text-muted-foreground">One bar per hour. Red marks server errors.</p>
        <div className="flex h-32 items-end gap-1" role="img" aria-label="Requests per hour over the last 24 hours">
          {s.traffic.map((t) => (
            <div key={t.hour} className="flex h-full flex-1 flex-col justify-end" title={`${fmtUtc(t.hour)} UTC: ${t.requests} requests, ${t.errors} errors`}>
              <div className="rounded-t-sm bg-destructive" style={{ height: `${(t.errors / peak) * 100}%` }} />
              <div className={`bg-primary/70 ${t.errors ? "" : "rounded-t-sm"}`} style={{ height: `${((t.requests - t.errors) / peak) * 100}%`, minHeight: t.requests ? 2 : 0 }} />
            </div>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground"><span>24 h ago</span><span>now</span></div>
      </Card>

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h2 className="text-xl font-semibold">Failed AI jobs</h2></div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Job</TableHead><TableHead>When (UTC)</TableHead><TableHead>Why it failed</TableHead><TableHead className="text-right tabular-nums">Tries</TableHead></TableRow></TableHeader>
            <TableBody>
              {s.failed_jobs.map((j) => (
                <TableRow key={j.id}>
                  <TableCell><Badge variant="secondary">{j.type}</Badge> <code className="text-xs">{j.id.slice(0, 8)}</code></TableCell>
                  <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{fmtUtc(j.created_at)}</TableCell>
                  <TableCell className="text-sm">{j.error ?? "No message"}</TableCell>
                  <TableCell className="text-right tabular-nums">{j.attempts}</TableCell>
                </TableRow>
              ))}
              {!s.failed_jobs.length && <TableRow><TableCell colSpan={4} className="empty">No failed jobs.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </div>
      </Card>
    </>
  );
}
