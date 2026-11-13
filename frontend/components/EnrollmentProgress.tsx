import Link from "next/link";
import type { components } from "@/lib/api-client/schema";
import { ENR_STATUS, ENR_TONE, STATUS_LABEL, STATUS_TONE, fmtTs, masteryTone, relDay } from "@/lib/format";
import { MeterBar } from "./MeterBar";
import { RingProgress } from "./RingProgress";
import { TaskRow } from "./TaskRow";
import { Alert } from "@/components/ui/alert";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Enr = components["schemas"]["EnrollmentDetail"];

const resultBadge = (passed: boolean | null | undefined): [string, BadgeTone] =>
  passed == null ? ["Diagnostic", "secondary"] : passed ? ["Passed", "success"] : ["Below pass mark", "destructive"];

export function EnrollmentProgress({
  e, readonly = false, actions,
}: { e: Enr; readonly?: boolean; actions?: React.ReactNode }) {
  const pending = e.tasks.filter((t) => !t.done).slice(0, 6);
  return (
    <section className="space-y-5">
      <Card style={{ borderTop: `4px solid ${e.accent ?? "var(--primary)"}` }} className="gap-0 p-6">
        <div className="flex flex-wrap items-center gap-6">
          <RingProgress value={e.overall} size={96} stroke={8} tone={masteryTone(e.overall, e.threshold)} />
          <div className="min-w-0 flex-1">
            <div className="eyebrow">{e.code}</div>
            <h2 className="mb-1.5 mt-0.5 text-2xl font-semibold">{e.title}</h2>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={ENR_TONE[e.status]}>{ENR_STATUS[e.status]}</Badge>
              <span className="text-sm text-muted-foreground">
                Pre-test {Math.round(e.pretest_score ?? 0)}% · {e.plan_done} of {e.plan_total} plan tasks done · pass mark {e.threshold}%
              </span>
            </div>
          </div>
          {actions}
        </div>
        {e.latest_day_status && (
          <Alert className="border-success/30 bg-success/10 text-success mt-4">
            <b>{e.latest_day_status.message}</b> <span className="opacity-70">· {relDay(e.latest_day_status.date, e.today)}</span>
          </Alert>
        )}
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card className="gap-0 py-0">
          <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Mastery by topic</h3><span className="text-xs text-muted-foreground">Crimson marker = pass mark</span></div>
          <div className="px-6 py-4 space-y-5">
            {e.topic_detail.map((t) => (
              <div key={t.id}>
                <div className="mb-1.5 flex justify-between text-sm"><b>{t.title}</b><span className="tabular-nums">{t.mastery}%</span></div>
                <MeterBar value={t.mastery} threshold={e.threshold} label={t.title} />
                <ul className="mt-2.5 text-sm">
                  {t.subtopics.map((s) => (
                    <li key={s.id} className="flex items-center gap-2 py-1">
                      {readonly ? <span className="flex-1">{s.title}</span> : (
                        <Link href={`/student/courses/${e.course_id}/subtopics/${s.id}`} className="flex-1 hover:text-primary hover:underline">{s.title}</Link>
                      )}
                      <span className="text-xs capitalize text-muted-foreground">{s.level}</span>
                      <Badge variant={STATUS_TONE[s.status]}>{STATUS_LABEL[s.status]}</Badge>
                      <span className="w-9 text-right tabular-nums">{s.mastery}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="gap-0 py-0">
            <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Upcoming tasks</h3><span className="text-xs text-muted-foreground">{e.pending_count} remaining</span></div>
            <div className="px-6 py-4 !py-1.5">
              {pending.length ? pending.map((t) => (
                <TaskRow key={t.id} task={t} courseId={e.course_id} showDate locked={readonly} today={e.today} />
              )) : <p className="my-3 text-sm text-muted-foreground">No tasks remaining.</p>}
            </div>
          </Card>
          <Card className="gap-0 py-0">
            <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Daily status</h3></div>
            <div className="px-6 py-4 !py-1.5">
              {!e.day_statuses.length && <p className="my-3 text-sm text-muted-foreground">No days completed yet.</p>}
              {e.day_statuses.map((d) => (
                <div key={d.id} className="task done">
                  <span className="tick">✓</span>
                  <div className="flex-1"><div className="t-title !text-foreground !no-underline">{d.message}</div><div className="t-meta">{relDay(d.date, e.today)}</div></div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Quiz history</h3><span className="text-xs text-muted-foreground">
            {e.history.length} attempts
            {!readonly && <> · <Link href="/student/history" className="text-primary hover:underline">View all</Link></>}
          </span></div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>When</TableHead><TableHead>Assessment</TableHead><TableHead className="text-right tabular-nums">Score</TableHead><TableHead>Result</TableHead></TableRow></TableHeader>
            <TableBody>
              {e.history.slice(0, 12).map((a) => {
                const [label, tone] = resultBadge(a.passed);
                return (
                  <TableRow key={a.id}>
                    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{fmtTs(a.created_at)}</TableCell>
                    <TableCell>{a.title}</TableCell>
                    <TableCell className="text-right tabular-nums">{Math.round(a.score)}%</TableCell>
                    <TableCell><Badge variant={tone}>{label}</Badge></TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Card>
    </section>
  );
}
