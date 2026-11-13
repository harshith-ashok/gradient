import Link from "next/link";
import { MeterBar } from "@/components/MeterBar";
import { ENR_STATUS, ENR_TONE, masteryTone, relDay } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const STATUSES = ["on-track", "attention", "completed"] as const;
const PAGE_SIZE = 15;
const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);

type Scope = "admin" | "faculty";

/** Student progress table, shared by the dean/admin (all courses) and faculty (own courses only) views. */
export async function StudentProgress({ scope, sp }: { scope: Scope; sp: Record<string, string | string[] | undefined> }) {
  const q = one(sp.q) ?? "";
  const courseId = one(sp.course_id) ?? "";
  const status = STATUSES.find((s) => s === one(sp.status));
  const page = Math.max(1, Number(one(sp.page)) || 1);

  const api = await serverApi();
  const query = { q, course_id: courseId || undefined, status, page, page_size: PAGE_SIZE };
  const data = unwrap(
    scope === "admin"
      ? await api.GET("/api/v1/admin/overview", { params: { query } })
      : await api.GET("/api/v1/faculty/students", { params: { query } }),
  );
  const base = scope === "admin" ? "/admin" : "/faculty/students";
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const link = (p: number) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (courseId) params.set("course_id", courseId);
    if (status) params.set("status", status);
    if (p > 1) params.set("page", String(p));
    const qs = params.toString();
    return qs ? `${base}?${qs}` : base;
  };
  const filtered = Boolean(q || courseId || status);

  return (
    <>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          [data.kpis.students, "Students registered", false],
          [data.kpis.active_learners, "Students enrolled in a course", false],
          [`${data.kpis.average_progress}%`, "Average overall progress", false],
          [data.kpis.need_attention, "Enrolments needing attention", data.kpis.need_attention > 0],
        ].map(([v, l, warn]) => (
          <Card key={String(l)} className="gap-0 p-6">
            <div className={` text-4xl font-semibold tabular-nums ${warn ? "text-warning" : ""}`}>{v}</div>
            <div className="mt-1 text-sm text-muted-foreground">{l}</div>
          </Card>
        ))}
      </div>

      <Card className="gap-0 py-0 mb-6">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Courses</h3></div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Course</TableHead><TableHead className="text-right tabular-nums">Enrolled</TableHead><TableHead className="w-[30%]">Average progress</TableHead><TableHead className="text-right tabular-nums">Pass mark</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.courses.map((c) => (
                <TableRow key={c.id}>
                  <TableCell><b>{c.code}</b> · {c.title}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.enrolled}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="flex-1"><MeterBar value={c.average} threshold={c.threshold} label={c.title} /></div>
                      <span className="w-10 text-right text-sm tabular-nums">{c.average}%</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{c.threshold}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="gap-0 py-0">
        <form method="get" className="flex flex-wrap items-center gap-3 border-b border-border p-4">
          <label className="sr-only" htmlFor="q">Search students</label>
          <Input id="q" name="q" defaultValue={q} placeholder="Search by name, email or ID" className="!w-72" />
          <label className="sr-only" htmlFor="course">Course</label>
          <NativeSelect id="course" name="course_id" defaultValue={courseId} className="!w-auto">
            <option value="">All courses</option>
            {data.courses.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.title}</option>)}
          </NativeSelect>
          <label className="sr-only" htmlFor="status">Status</label>
          <NativeSelect id="status" name="status" defaultValue={status ?? ""} className="!w-auto">
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{ENR_STATUS[s]}</option>)}
          </NativeSelect>
          <Button type="submit" size="sm">Apply</Button>
          {filtered && <Link href={base} className="text-sm text-primary hover:underline">Clear</Link>}
          <span className="ml-auto text-sm text-muted-foreground">{data.total} {data.total === 1 ? "row" : "rows"}</span>
        </form>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow><TableHead>Student</TableHead><TableHead>Course</TableHead><TableHead className="min-w-[150px]">Overall</TableHead><TableHead>Mastery by topic</TableHead><TableHead className="min-w-[240px]">Upcoming tasks</TableHead><TableHead>Status</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {data.rows.map((r) => {
                const e = r.enrollment;
                return (
                  <TableRow key={r.student.id + (e?.course_id ?? "")} className="hover:bg-muted">
                    <TableCell>
                      <Link href={`${scope === "admin" ? "/admin" : "/faculty"}/students/${r.student.id}`} className="font-semibold hover:text-primary hover:underline">{r.student.name}</Link>
                      <div className="text-xs text-muted-foreground">{r.student.student_id} · {r.student.program}</div>
                    </TableCell>
                    {e ? (
                      <>
                        <TableCell><b>{e.code}</b><div className="text-xs text-muted-foreground">{e.title}</div></TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="flex-1"><MeterBar value={e.overall} threshold={e.threshold} label={`${r.student.name} overall`} /></div>
                            <b className="w-10 text-right tabular-nums">{e.overall}%</b>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex h-8 items-end gap-1" aria-hidden="true">
                            {e.topics.map((t) => {
                              const tone = masteryTone(t.mastery, e.threshold);
                              const color = tone === "ok" ? "bg-success" : tone === "warn" ? "bg-warning" : "bg-destructive";
                              return <span key={t.id} title={`${t.title}: ${t.mastery}%`} className={`w-4 rounded-sm ${color}`} style={{ height: `${Math.max(8, t.mastery)}%` }} />;
                            })}
                          </div>
                          <div className="mt-1 text-xs text-muted-foreground">{e.topics.map((t) => `${t.mastery}%`).join(" · ")}</div>
                        </TableCell>
                        <TableCell>
                          {e.upcoming.slice(0, 2).map((t) => (
                            <div key={t.id} className="text-sm">{t.title} <span className="text-muted-foreground">· {relDay(t.date, e.today)}</span></div>
                          ))}
                          {!e.upcoming.length && <span className="text-sm text-muted-foreground">None</span>}
                        </TableCell>
                        <TableCell><Badge variant={ENR_TONE[e.status]}>{ENR_STATUS[e.status]}</Badge></TableCell>
                      </>
                    ) : (
                      <TableCell colSpan={5} className="text-sm text-muted-foreground">Not enrolled in any course</TableCell>
                    )}
                  </TableRow>
                );
              })}
              {!data.rows.length && <TableRow><TableCell colSpan={6} className="empty">No students match these filters.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </div>

        {pages > 1 && (
          <nav aria-label="Pagination" className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
            {page > 1 ? <Link href={link(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>← Previous</Link> : <span />}
            <span className="text-muted-foreground">Page {page} of {pages}</span>
            {page < pages ? <Link href={link(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>Next →</Link> : <span />}
          </nav>
        )}
      </Card>
    </>
  );
}
