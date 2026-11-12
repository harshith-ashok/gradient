import type { Metadata } from "next";
import Link from "next/link";
import { MeterBar } from "@/components/MeterBar";
import { PageHeader } from "@/components/PageHeader";
import { ENR_STATUS, ENR_TONE, masteryTone, relDay } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Student progress" };

const STATUSES = ["on-track", "attention", "completed"] as const;
const PAGE_SIZE = 15;
const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);

export default async function AdminDashboard({ searchParams }: PageProps<"/admin">) {
  const sp = await searchParams;
  const q = one(sp.q) ?? "";
  const courseId = one(sp.course_id) ?? "";
  const status = STATUSES.find((s) => s === one(sp.status));
  const page = Math.max(1, Number(one(sp.page)) || 1);

  const api = await serverApi();
  const data = unwrap(
    await api.GET("/api/v1/admin/overview", {
      params: { query: { q, course_id: courseId || undefined, status, page, page_size: PAGE_SIZE } },
    }),
  );
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const link = (p: number) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (courseId) params.set("course_id", courseId);
    if (status) params.set("status", status);
    if (p > 1) params.set("page", String(p));
    const qs = params.toString();
    return qs ? `/admin?${qs}` : "/admin";
  };
  const filtered = Boolean(q || courseId || status);

  return (
    <>
      <PageHeader
        eyebrow="Management"
        title="Student progress"
        lede="Overall progress, per-topic mastery and upcoming tasks for every student."
        actions={<Link href="/admin/settings" className="btn btn-secondary">Quiz pass mark settings</Link>}
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          [data.kpis.students, "Students registered", false],
          [data.kpis.active_learners, "Students enrolled in a course", false],
          [`${data.kpis.average_progress}%`, "Average overall progress", false],
          [data.kpis.need_attention, "Enrolments needing attention", data.kpis.need_attention > 0],
        ].map(([v, l, warn]) => (
          <div key={String(l)} className="card card-pad">
            <div className={`font-serif text-4xl tabular-nums ${warn ? "text-warn" : ""}`}>{v}</div>
            <div className="mt-1 text-sm text-muted">{l}</div>
          </div>
        ))}
      </div>

      <div className="card mb-6">
        <div className="card-head"><h3 className="text-lg font-semibold">Courses</h3></div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>Course</th><th className="num">Enrolled</th><th className="w-[30%]">Average progress</th><th className="num">Pass mark</th></tr></thead>
            <tbody>
              {data.courses.map((c) => (
                <tr key={c.id}>
                  <td><b>{c.code}</b> · {c.title}</td>
                  <td className="num">{c.enrolled}</td>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="flex-1"><MeterBar value={c.average} threshold={c.threshold} label={c.title} /></div>
                      <span className="w-10 text-right text-sm tabular-nums">{c.average}%</span>
                    </div>
                  </td>
                  <td className="num">{c.threshold}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <form method="get" className="flex flex-wrap items-center gap-3 border-b border-line-soft p-4">
          <label className="sr-only" htmlFor="q">Search students</label>
          <input id="q" name="q" defaultValue={q} className="input !w-72" placeholder="Search by name, email or ID" />
          <label className="sr-only" htmlFor="course">Course</label>
          <select id="course" name="course_id" defaultValue={courseId} className="input !w-auto">
            <option value="">All courses</option>
            {data.courses.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.title}</option>)}
          </select>
          <label className="sr-only" htmlFor="status">Status</label>
          <select id="status" name="status" defaultValue={status ?? ""} className="input !w-auto">
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{ENR_STATUS[s]}</option>)}
          </select>
          <button type="submit" className="btn btn-sm">Apply</button>
          {filtered && <Link href="/admin" className="text-sm text-crimson hover:underline">Clear</Link>}
          <span className="ml-auto text-sm text-muted">{data.total} {data.total === 1 ? "row" : "rows"}</span>
        </form>

        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr><th>Student</th><th>Course</th><th className="min-w-[150px]">Overall</th><th>Mastery by topic</th><th className="min-w-[240px]">Upcoming tasks</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.rows.map((r) => {
                const e = r.enrollment;
                return (
                  <tr key={r.student.id + (e?.course_id ?? "")} className="hover:bg-ink-50">
                    <td>
                      <Link href={`/admin/students/${r.student.id}`} className="font-semibold hover:text-crimson hover:underline">{r.student.name}</Link>
                      <div className="text-xs text-muted">{r.student.student_id} · {r.student.program}</div>
                    </td>
                    {e ? (
                      <>
                        <td><b>{e.code}</b><div className="text-xs text-muted">{e.title}</div></td>
                        <td>
                          <div className="flex items-center gap-3">
                            <div className="flex-1"><MeterBar value={e.overall} threshold={e.threshold} label={`${r.student.name} overall`} /></div>
                            <b className="w-10 text-right tabular-nums">{e.overall}%</b>
                          </div>
                        </td>
                        <td>
                          <div className="flex h-8 items-end gap-1" aria-hidden="true">
                            {e.topics.map((t) => {
                              const tone = masteryTone(t.mastery, e.threshold);
                              const color = tone === "ok" ? "bg-ok" : tone === "warn" ? "bg-[#c4871f]" : "bg-bad";
                              return <span key={t.id} title={`${t.title}: ${t.mastery}%`} className={`w-4 rounded-sm ${color}`} style={{ height: `${Math.max(8, t.mastery)}%` }} />;
                            })}
                          </div>
                          <div className="mt-1 text-xs text-muted">{e.topics.map((t) => `${t.mastery}%`).join(" · ")}</div>
                        </td>
                        <td>
                          {e.upcoming.slice(0, 2).map((t) => (
                            <div key={t.id} className="text-sm">{t.title} <span className="text-muted">· {relDay(t.date, e.today)}</span></div>
                          ))}
                          {!e.upcoming.length && <span className="text-sm text-muted">None</span>}
                        </td>
                        <td><span className={`badge ${ENR_TONE[e.status]}`}>{ENR_STATUS[e.status]}</span></td>
                      </>
                    ) : (
                      <td colSpan={5} className="text-sm text-muted">Not enrolled in any course</td>
                    )}
                  </tr>
                );
              })}
              {!data.rows.length && <tr><td colSpan={6} className="empty">No students match these filters.</td></tr>}
            </tbody>
          </table>
        </div>

        {pages > 1 && (
          <nav aria-label="Pagination" className="flex items-center justify-between border-t border-line-soft px-4 py-3 text-sm">
            {page > 1 ? <Link href={link(page - 1)} className="btn btn-secondary btn-sm">← Previous</Link> : <span />}
            <span className="text-muted">Page {page} of {pages}</span>
            {page < pages ? <Link href={link(page + 1)} className="btn btn-secondary btn-sm">Next →</Link> : <span />}
          </nav>
        )}
      </div>
    </>
  );
}
