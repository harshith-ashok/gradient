import type { Metadata } from "next";
import Link from "next/link";
import { MeterBar } from "@/components/MeterBar";
import { PageHeader } from "@/components/PageHeader";
import { RingProgress } from "@/components/RingProgress";
import { ENR_STATUS, ENR_TONE, STATUS_LABEL, STATUS_TONE, masteryTone, relDay } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";

type Props = PageProps<"/student/courses/[courseId]">;

async function load(courseId: string) {
  const api = await serverApi();
  return unwrap(await api.GET("/api/v1/student/courses/{course_id}", { params: { path: { course_id: courseId } } }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: (await load((await params).courseId)).title };
}

export default async function CoursePage({ params }: Props) {
  const course = await load((await params).courseId);
  const enr = course.enrollment;
  const subInfo = new Map(enr?.topic_detail.flatMap((t) => t.subtopics.map((s) => [s.id, s] as const)));
  const topicMastery = new Map(enr?.topic_detail.map((t) => [t.id, t.mastery] as const));
  const next = enr?.tasks.find((t) => !t.done);
  const base = `/student/courses/${course.id}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Courses", to: "/student/courses" }, { label: course.code }]}
        eyebrow={`${course.code} · ${course.department}`}
        title={course.title}
        lede={course.description}
        actions={enr ? (
          <>
            <Link href={`${base}/plan`} className={buttonVariants()}>Study plan</Link>
            <Link href="/student/practice" className={buttonVariants({ variant: "outline" })}>Practice quiz</Link>
          </>
        ) : (
          <Link href={`${base}/pretest`} className={buttonVariants({ size: "lg" })}>Enrol and take the pre-test</Link>
        )}
      />

      <div className="mb-8 grid items-stretch gap-5 md:grid-cols-3">
        <Card className="gap-0 p-6 text-sm">
          <div className="text-xs text-muted-foreground">Instructor</div><div className="font-medium">{course.instructor}</div>
          <div className="mt-2.5 text-xs text-muted-foreground">Level · credits</div><div>{course.level} · {course.credits} credits</div>
          <div className="mt-2.5 text-xs text-muted-foreground">Quiz pass mark</div><div>{course.threshold}%</div>
        </Card>
        {enr ? (
          <>
            <Card className="gap-0 p-6 flex items-center gap-5">
              <RingProgress value={enr.overall} size={84} stroke={8} tone={masteryTone(enr.overall, enr.threshold)} />
              <div>
                <div className="text-xs text-muted-foreground">Overall mastery</div>
                <Badge variant={ENR_TONE[enr.status]}>{ENR_STATUS[enr.status]}</Badge>
                <div className="mt-1.5 text-sm text-muted-foreground">Pre-test {Math.round(enr.pretest_score ?? 0)}%</div>
              </div>
            </Card>
            <Card className="gap-0 p-6 text-sm">
              <div className="text-xs text-muted-foreground">Next up</div>
              {next ? (
                <><div className="font-medium">{next.title}</div><div className="text-muted-foreground">{relDay(next.date, enr.today)} · {next.minutes} min</div></>
              ) : <div>Plan complete</div>}
              <Link href={`${base}/plan`} className="mt-1 inline-block text-primary hover:underline">View full plan →</Link>
            </Card>
          </>
        ) : (
          <Alert className="bg-muted md:col-span-2">
            <b>Not enrolled yet.</b>
            <p className="mt-1.5">Take the pre-test to unlock your personalised study plan, quizzes and progress tracking. You can still read every summary and flashcard.</p>
          </Alert>
        )}
      </div>

      <section>
        <h2 className="mb-3 text-2xl font-semibold">Topics and sub-topics</h2>
        <div className="space-y-4">
          {course.topics.map((t, ti) => (
            <details key={t.id} open className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10 group">
              <summary className="flex cursor-pointer list-none items-center gap-4 border-b border-border px-6 py-4">
                <div className="flex-1">
                  <div className="eyebrow">Topic {ti + 1}</div>
                  <h3 className="text-xl font-semibold">{t.title}</h3>
                </div>
                {enr && <div className="hidden w-36 sm:block"><MeterBar value={topicMastery.get(t.id) ?? 0} threshold={enr.threshold} thin label={t.title} /></div>}
                <span className="text-muted-foreground group-open:rotate-45" aria-hidden="true">＋</span>
              </summary>
              <ul>
                {t.subtopics.map((s) => {
                  const info = subInfo.get(s.id);
                  return (
                    <li key={s.id} className="flex items-center gap-4 border-b border-border px-6 py-3 last:border-0">
                      <div className="flex-1">
                        <Link href={`${base}/subtopics/${s.id}`} className="font-medium hover:text-primary hover:underline">{s.title}</Link>
                        <div className="text-sm text-muted-foreground">{s.description}</div>
                      </div>
                      {info && (
                        <>
                          <Badge variant={STATUS_TONE[info.status]}>{STATUS_LABEL[info.status]}</Badge>
                          <span className="w-10 text-right text-sm tabular-nums">{info.mastery}%</span>
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
