import Link from "next/link";
import type { components } from "@/lib/api-client/schema";
import { ENR_STATUS, ENR_TONE, STATUS_LABEL, STATUS_TONE, fmtTs, masteryTone, relDay } from "@/lib/format";
import { MeterBar } from "./MeterBar";
import { RingProgress } from "./RingProgress";
import { TaskRow } from "./TaskRow";

type Enr = components["schemas"]["EnrollmentDetail"];

const resultBadge = (passed: boolean | null | undefined) =>
  passed == null ? ["Diagnostic", "badge-info"] : passed ? ["Passed", "badge-ok"] : ["Below pass mark", "badge-bad"];

export function EnrollmentProgress({
  e, readonly = false, actions,
}: { e: Enr; readonly?: boolean; actions?: React.ReactNode }) {
  const pending = e.tasks.filter((t) => !t.done).slice(0, 6);
  return (
    <section className="space-y-5">
      <div className="card card-pad" style={{ borderTop: `4px solid ${e.accent ?? "var(--crimson)"}` }}>
        <div className="flex flex-wrap items-center gap-6">
          <RingProgress value={e.overall} size={96} stroke={8} tone={masteryTone(e.overall, e.threshold)} />
          <div className="min-w-0 flex-1">
            <div className="eyebrow">{e.code}</div>
            <h2 className="mb-1.5 mt-0.5 text-2xl font-semibold">{e.title}</h2>
            <div className="flex flex-wrap items-center gap-3">
              <span className={`badge ${ENR_TONE[e.status]}`}>{ENR_STATUS[e.status]}</span>
              <span className="text-sm text-muted">
                Pre-test {Math.round(e.pretest_score ?? 0)}% · {e.plan_done} of {e.plan_total} plan tasks done · pass mark {e.threshold}%
              </span>
            </div>
          </div>
          {actions}
        </div>
        {e.latest_day_status && (
          <div className="callout callout-ok mt-4">
            <b>{e.latest_day_status.message}</b> <span className="opacity-70">· {relDay(e.latest_day_status.date, e.today)}</span>
          </div>
        )}
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <div className="card">
          <div className="card-head"><h3 className="text-lg font-semibold">Mastery by topic</h3><span className="text-xs text-muted">Crimson marker = pass mark</span></div>
          <div className="card-body space-y-5">
            {e.topic_detail.map((t) => (
              <div key={t.id}>
                <div className="mb-1.5 flex justify-between text-sm"><b>{t.title}</b><span className="tabular-nums">{t.mastery}%</span></div>
                <MeterBar value={t.mastery} threshold={e.threshold} label={t.title} />
                <ul className="mt-2.5 text-sm">
                  {t.subtopics.map((s) => (
                    <li key={s.id} className="flex items-center gap-2 py-1">
                      {readonly ? <span className="flex-1">{s.title}</span> : (
                        <Link href={`/student/courses/${e.course_id}/subtopics/${s.id}`} className="flex-1 hover:text-crimson hover:underline">{s.title}</Link>
                      )}
                      <span className="text-xs capitalize text-faint">{s.level}</span>
                      <span className={`badge ${STATUS_TONE[s.status]}`}>{STATUS_LABEL[s.status]}</span>
                      <span className="w-9 text-right tabular-nums">{s.mastery}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card">
            <div className="card-head"><h3 className="text-lg font-semibold">Upcoming tasks</h3><span className="text-xs text-muted">{e.pending_count} remaining</span></div>
            <div className="card-body !py-1.5">
              {pending.length ? pending.map((t) => (
                <TaskRow key={t.id} task={t} courseId={e.course_id} showDate locked={readonly} today={e.today} />
              )) : <p className="my-3 text-sm text-muted">No tasks remaining.</p>}
            </div>
          </div>
          <div className="card">
            <div className="card-head"><h3 className="text-lg font-semibold">Daily status</h3></div>
            <div className="card-body !py-1.5">
              {!e.day_statuses.length && <p className="my-3 text-sm text-muted">No days completed yet.</p>}
              {e.day_statuses.map((d) => (
                <div key={d.id} className="task done">
                  <span className="tick">✓</span>
                  <div className="flex-1"><div className="t-title !text-ink !no-underline">{d.message}</div><div className="t-meta">{relDay(d.date, e.today)}</div></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h3 className="text-lg font-semibold">Quiz history</h3><span className="text-xs text-muted">
            {e.history.length} attempts
            {!readonly && <> · <Link href="/student/history" className="text-crimson hover:underline">View all</Link></>}
          </span></div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>When</th><th>Assessment</th><th className="num">Score</th><th>Result</th></tr></thead>
            <tbody>
              {e.history.slice(0, 12).map((a) => {
                const [label, tone] = resultBadge(a.passed);
                return (
                  <tr key={a.id}>
                    <td className="whitespace-nowrap text-sm text-muted">{fmtTs(a.created_at)}</td>
                    <td>{a.title}</td>
                    <td className="num">{Math.round(a.score)}%</td>
                    <td><span className={`badge ${tone}`}>{label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
