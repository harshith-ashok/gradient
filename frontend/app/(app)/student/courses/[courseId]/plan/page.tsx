import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { PlanSettings } from "@/components/PlanSettings";
import { TaskRow } from "@/components/TaskRow";
import { fmtDay, fmtTs } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Study plan" };

const NOTICE_TONE = { reschedule: "warning", recalc: "secondary", info: "default" } as const;
const NOTICE_LABEL = { reschedule: "Rescheduled", recalc: "Recalculated", info: "Created" } as const;

export default async function PlanPage({ params }: PageProps<"/student/courses/[courseId]/plan">) {
  const { courseId } = await params;
  const api = await serverApi();
  const course = unwrap(await api.GET("/api/v1/student/courses/{course_id}", { params: { path: { course_id: courseId } } }));
  const e = course.enrollment;

  if (!e) {
    return (
      <Card className="gap-0 py-0 empty">
        <h3>No plan yet</h3>
        <p>Your plan is created from the pre-test.</p>
        <Link href={`/student/courses/${courseId}/pretest`} className={buttonVariants()}>Take the pre-test</Link>
      </Card>
    );
  }

  const byDay = new Map<number, typeof e.tasks>();
  for (const t of e.tasks) byDay.set(t.day, [...(byDay.get(t.day) ?? []), t]);
  const days = [...byDay.entries()].sort((a, b) => a[0] - b[0]).map(([day, tasks]) => ({
    day, tasks, date: tasks[0].date, minutes: tasks.reduce((s, t) => s + t.minutes, 0),
    done: tasks.every((t) => t.done), status: e.day_statuses.find((d) => d.day_index === day),
    today: tasks[0].date === e.today,
  }));

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Courses", to: "/student/courses" }, { label: course.code, to: `/student/courses/${courseId}` }, { label: "Study plan" }]}
        eyebrow="Personalised study plan"
        title={course.title}
        lede={`Day ${e.day_number} of your plan · ${e.plan_done} of ${e.plan_total} tasks done`}
        actions={<PlanSettings courseId={courseId} minutes={e.minutes_per_day} days={e.target_days} planning={e.planning} />}
      />
      {e.planning && (
        <Card role="status" style={{ borderLeftColor: "var(--primary)" }} className="block gap-0 py-0 mb-4 border-l-4 px-4 py-3 text-sm">
          The AI planner is tailoring your study time to your results. Your plan below is already usable and will
          update in a moment.
        </Card>
      )}
      <Card className={cn("mb-4 block gap-0 px-4 py-3 text-sm", !e.plan_window.fits && "border-l-4 border-l-warning")}>
        {e.plan_window.fits ? (
          <>Everything is scheduled to finish by <strong>{fmtDay(e.plan_window.finish_date ?? e.plan_window.ends_on)}</strong>,
          inside your {e.target_days}-day time frame (ends {fmtDay(e.plan_window.ends_on)}).</>
        ) : (
          <>At {e.minutes_per_day} minutes a day this plan does not fit your {e.target_days}-day time frame. About{" "}
          <strong>{e.plan_window.needed_minutes_per_day} minutes a day</strong>, or a longer time frame, would cover everything.</>
        )}
      </Card>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          {days.map((d) => (
            <Card key={d.day} style={d.today ? { borderColor: "var(--primary)" } : undefined} className="gap-0 py-0">
              <div className="flex items-center justify-between gap-4 border-b px-6 py-4 !py-3">
                <div className="flex items-center gap-3">
                  <span className=" text-lg font-semibold">Day {d.day + 1}</span>
                  <span className="text-sm text-muted-foreground">{fmtDay(d.date)}</span>
                  {d.today && <Badge variant="default">Today</Badge>}
                </div>
                {d.status ? <Badge variant="success">{d.status.message}</Badge>
                  : d.done ? <Badge variant="success">Completed</Badge>
                  : <span className="text-sm text-muted-foreground">{d.minutes} min</span>}
              </div>
              <div className="px-6 py-4 !py-1">
                {d.tasks.map((t) => <TaskRow key={t.id} task={t} courseId={courseId} today={e.today} />)}
              </div>
            </Card>
          ))}
        </div>
        <aside className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10 lg:sticky lg:top-4">
          <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">Plan updates</h3></div>
          <div className="px-6 py-4 divide-y divide-border !py-1">
            {e.notices.map((n) => (
              <div key={n.id} className="space-y-1 py-3 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant={NOTICE_TONE[n.kind]}>{NOTICE_LABEL[n.kind]}</Badge>
                  <span className="text-xs text-muted-foreground">{fmtTs(n.created_at)}</span>
                </div>
                <div>{n.text}</div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}
