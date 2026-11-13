import type { Metadata } from "next";
import Link from "next/link";
import { MeterBar } from "@/components/MeterBar";
import { RingProgress } from "@/components/RingProgress";
import { TaskRow } from "@/components/TaskRow";
import { ENR_STATUS, ENR_TONE, firstName, fmtTs, masteryTone, relDay } from "@/lib/format";
import { currentUser } from "@/lib/session-server";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const metadata: Metadata = { title: "Dashboard" };

export default async function StudentDashboard() {
  const user = await currentUser();
  const api = await serverApi();
  const data = unwrap(await api.GET("/api/v1/student/dashboard"));
  const avg = data.enrollments.length
    ? Math.round(data.enrollments.reduce((n, e) => n + e.overall, 0) / data.enrollments.length) : 0;
  const left = data.today.filter((t) => !t.done).length;
  const todayOf = (courseId: string) => data.enrollments.find((e) => e.course_id === courseId)?.today;
  // The server's calendar date (plan days roll over in its timezone); omitted before any enrolment.
  const dateLabel = data.enrollments[0]
    ? new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
        .format(new Date(`${data.enrollments[0].today}T12:00:00`))
    : "Your learning portal";

  return (
    <>
      <section className="mb-10 overflow-hidden rounded-md bg-primary p-8 text-white md:p-10">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#c9a9a0]">{dateLabel}</p>
        <h1 className="mt-2 text-4xl font-semibold">
          Welcome back, <em className="text-primary-foreground/70">{firstName(user.name)}</em>
        </h1>
        <p className="mt-2 max-w-xl text-[#e6d3cd]">Your plan reschedules itself when a topic needs more time. Here is where you stand today.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/student/courses" className={buttonVariants({ variant: "outline" })}>Browse courses</Link>
          <Link href="/student/practice" className={buttonVariants()}>Quiz me on… →</Link>
        </div>
        {data.enrollments.length > 0 && (
          <dl className="mt-8 flex flex-wrap gap-10 border-t border-white/15 pt-6">
            <div><dt className="order-2 text-xs text-[#c9a9a0]">Average mastery</dt><dd className=" text-3xl">{avg}<small className="text-lg">%</small></dd></div>
            <div><dt className="text-xs text-[#c9a9a0]">Tasks left today</dt><dd className=" text-3xl">{left}</dd></div>
            <div><dt className="text-xs text-[#c9a9a0]">{data.enrollments.length === 1 ? "Course" : "Courses"} in progress</dt><dd className=" text-3xl">{data.enrollments.length}</dd></div>
          </dl>
        )}
      </section>

      {!data.enrollments.length ? (
        <Card className="gap-0 py-0 empty">
          <h3>You have not started a course yet</h3>
          <p>Pick a course from the catalogue. You will take a short pre-test and receive a personalised study plan.</p>
          <Link href="/student/courses" className={buttonVariants()}>Choose a course</Link>
        </Card>
      ) : (
        <>
          <div className="grid items-start gap-5 lg:grid-cols-2">
            <Card className="gap-0 py-0">
              <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h2 className="text-xl font-semibold">Today’s agenda</h2><Badge variant="secondary">{left} to do</Badge></div>
              <div className="px-6 py-4 !py-1.5">
                {!data.today.length && <p className="my-3.5 text-muted-foreground">Nothing scheduled for today. You can work ahead from your study plan.</p>}
                {data.today.map((t) => (
                  <TaskRow key={t.id} task={t} courseId={t.course_id} showCourse={t.course_code} today={todayOf(t.course_id)} />
                ))}
              </div>
            </Card>
            <Card className="gap-0 py-0">
              <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h2 className="text-xl font-semibold">End-of-day status</h2></div>
              <div className="px-6 py-4 !py-1.5">
                {!data.statuses.length && <p className="my-3.5 text-muted-foreground">Finish every task in a day to receive your daily status.</p>}
                {data.statuses.map((s) => (
                  <div key={s.id} className="task done">
                    <span className="tick">✓</span>
                    <div className="flex-1"><div className="t-title !text-foreground !no-underline">{s.message}</div><div className="t-meta">{s.course_code} · {relDay(s.date, todayOf(s.course_id))}</div></div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <section className="mt-12">
            <h2 className="mb-4 text-2xl font-semibold">My courses</h2>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {data.enrollments.map((e) => (
                <Card key={e.course_id} style={{ borderTop: `4px solid ${e.accent ?? "var(--primary)"}` }} className="gap-0 py-0 flex flex-col justify-between p-6">
                  <div>
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <div className="eyebrow">{e.code}</div>
                        <h3 className="my-1 text-xl font-semibold">{e.title}</h3>
                        <Badge variant={ENR_TONE[e.status]}>{ENR_STATUS[e.status]}</Badge>
                      </div>
                      <RingProgress value={e.overall} tone={masteryTone(e.overall, e.threshold)} />
                    </div>
                    <div className="mt-4 space-y-2.5">
                      {e.topics.map((t) => (
                        <div key={t.id}>
                          <div className="mb-1 flex justify-between text-xs text-muted-foreground"><span>{t.title}</span><span className="tabular-nums">{t.mastery}%</span></div>
                          <MeterBar value={t.mastery} threshold={e.threshold} thin label={t.title} />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="mt-5 flex items-center justify-between gap-3">
                    <span className="truncate text-sm text-muted-foreground">{e.upcoming[0] ? `Next: ${e.upcoming[0].title}` : "Plan complete"}</span>
                    <Link href={`/student/courses/${e.course_id}`} className={buttonVariants({ size: "sm" })}>Continue</Link>
                  </div>
                </Card>
              ))}
            </div>
          </section>

          {data.recent.length > 0 && (
            <section className="mt-12">
              <div className="mb-4 flex items-baseline justify-between">
                <h2 className="text-2xl font-semibold">Recent results</h2>
                <Link href="/student/progress" className="text-sm text-primary hover:underline">Full progress →</Link>
              </div>
              <Card className="gap-0 py-0 overflow-x-auto">
                <Table>
                  <TableHeader><TableRow><TableHead>When</TableHead><TableHead>Assessment</TableHead><TableHead className="text-right tabular-nums">Score</TableHead><TableHead>Result</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {data.recent.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{fmtTs(a.created_at)}</TableCell>
                        <TableCell>{a.title}</TableCell>
                        <TableCell className="text-right tabular-nums">{Math.round(a.score)}%</TableCell>
                        <TableCell>
                          <Badge variant={a.passed == null ? "secondary" : a.passed ? "success" : "destructive"}>
                            {a.passed == null ? "Diagnostic" : a.passed ? "Passed" : "Below pass mark"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </section>
          )}
        </>
      )}
    </>
  );
}
