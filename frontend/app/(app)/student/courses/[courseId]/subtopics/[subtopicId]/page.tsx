import type { Metadata } from "next";
import Link from "next/link";
import { MeterBar } from "@/components/MeterBar";
import { PageHeader } from "@/components/PageHeader";
import { STATUS_LABEL, STATUS_TONE, relDay } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { SubtopicTabs } from "./SubtopicTabs";
import { parseTab } from "./tabs";

type Props = PageProps<"/student/courses/[courseId]/subtopics/[subtopicId]">;

async function load(courseId: string, subtopicId: string) {
  const api = await serverApi();
  return unwrap(
    await api.GET("/api/v1/student/courses/{course_id}/subtopics/{subtopic_id}", {
      params: { path: { course_id: courseId, subtopic_id: subtopicId } },
    }),
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { courseId, subtopicId } = await params;
  return { title: (await load(courseId, subtopicId)).subtopic.title };
}

export default async function SubtopicPage({ params, searchParams }: Props) {
  const { courseId, subtopicId } = await params;
  const { tab } = await searchParams;
  const data = await load(courseId, subtopicId);
  const base = `/student/courses/${courseId}`;
  const m = data.mastery;
  const enrolled = m != null;
  const quizHref = `${base}/quiz?kind=subtopic&subtopicId=${subtopicId}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Courses", to: "/student/courses" }, { label: data.course_code, to: base }, { label: data.topic.title }]}
        eyebrow={data.topic.title}
        title={data.subtopic.title}
        lede={data.subtopic.description}
        actions={enrolled
          ? <Link href={quizHref} className="btn">Take the quiz</Link>
          : <Link href={`${base}/pretest`} className="btn">Enrol to take quizzes</Link>}
      />
      {m?.remediation && (
        <div className="callout callout-warn mb-5">
          <b>This sub-topic needs review.</b> Your last quiz score was {Math.round(m.last_score ?? 0)}%, below the {data.threshold}% pass
          mark. Work through the{" "}
          <Link href={`${base}/subtopics/${subtopicId}?tab=help`} className="underline">remediation material</Link>, then retake the quiz.
        </div>
      )}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <SubtopicTabs
          key={subtopicId + String(tab)}
          content={data.subtopic} initialTab={parseTab(tab)} courseId={courseId} subtopicId={subtopicId}
          enrolled={enrolled} studied={m?.studied ?? false}
          pendingStudy={data.tasks.some((t) => !t.done && t.type === "study")}
          pendingHelp={data.tasks.some((t) => !t.done && t.type === "remediation")}
        />
        <aside className="space-y-5">
          {m ? (
            <div className="card card-pad">
              <div className="flex items-center justify-between">
                <h4 className="font-sans font-semibold">Mastery</h4>
                <span className={`badge ${STATUS_TONE[m.status]}`}>{STATUS_LABEL[m.status]}</span>
              </div>
              <div className="my-2.5 font-serif text-4xl tabular-nums">{m.value}%</div>
              <MeterBar value={m.value} threshold={data.threshold} label="Mastery" />
              <p className="mt-2.5 text-xs text-muted">
                Pass mark {data.threshold}% · {m.attempts} quiz attempt{m.attempts === 1 ? "" : "s"}
                {m.last_score != null ? ` · last score ${Math.round(m.last_score)}%` : ""}
              </p>
              <p className="mt-1 text-xs text-muted">Level: <b className="capitalize">{m.level}</b></p>
            </div>
          ) : (
            <div className="card card-pad text-sm text-muted">
              Enrol in this course to track mastery, take quizzes and get a personalised plan.
            </div>
          )}
          {enrolled && (
            <div className="card card-pad">
              <h4 className="mb-2 font-sans font-semibold">In your plan</h4>
              {data.tasks.map((t) => (
                <div key={t.id} className={`task ${t.done ? "done" : ""} !py-2`}>
                  <span className="tick">{t.done ? "✓" : ""}</span>
                  <div className="flex-1">
                    <div className="t-title !text-[13.5px]">{t.title}</div>
                    <div className="t-meta">{t.done ? t.result : `Day ${t.day + 1} · ${relDay(t.date)}`}</div>
                  </div>
                </div>
              ))}
              {!data.tasks.length && <p className="text-sm text-muted">No tasks planned for this sub-topic.</p>}
            </div>
          )}
          <div className="flex justify-between gap-3 text-sm">
            {data.prev ? <Link href={`${base}/subtopics/${data.prev.id}`} className="text-crimson hover:underline">← {data.prev.title}</Link> : <span />}
            {data.next ? <Link href={`${base}/subtopics/${data.next.id}`} className="text-right text-crimson hover:underline">{data.next.title} →</Link> : <span />}
          </div>
        </aside>
      </div>
    </>
  );
}
