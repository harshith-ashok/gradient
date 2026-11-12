"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { TASK_LABEL, plural, relDay, taskHref } from "@/lib/format";
import { MeterBar } from "./MeterBar";
import { PageHeader } from "./PageHeader";
import { QuizRunner } from "./QuizRunner";
import { RingProgress } from "./RingProgress";
import { useToast } from "./Toast";

type Quiz = components["schemas"]["QuizStart"];
type Result = components["schemas"]["QuizResult"];
type Kind = components["schemas"]["QuizStartRequest"]["kind"];
type Phase = "loading" | "intro" | "running" | "result" | "error";

export function QuizSession({
  courseId, kind, topicId, subtopicId,
}: { courseId: string; kind: Kind; topicId?: string; subtopicId?: string }) {
  const toast = useToast();
  const [phase, setPhase] = useState<Phase>("loading");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const started = useRef(false);
  const isPre = kind === "pretest";
  const base = `/student/courses/${courseId}`;
  const backTo = subtopicId ? `${base}/subtopics/${subtopicId}` : base;

  const load = useCallback(async () => {
    setPhase("loading");
    setResult(null);
    const { data, error: err } = await api.POST("/api/v1/student/quizzes", {
      body: { course_id: courseId, kind, topic_id: topicId, subtopic_id: subtopicId },
    });
    if (data) { setQuiz(data); setPhase("intro"); }
    else { setError(errorMessage(err)); setPhase("error"); }
  }, [courseId, kind, topicId, subtopicId]);

  useEffect(() => {
    if (started.current) return; // React dev mode runs effects twice; open only one session
    started.current = true;
    load();
  }, [load]);

  async function submit(answers: Record<string, number>) {
    if (!quiz) return;
    setSubmitting(true);
    const { data, error: err, response } = await api.POST("/api/v1/student/quizzes/{quiz_id}/submit", {
      params: { path: { quiz_id: quiz.quiz_id } },
      body: { answers },
    });
    setSubmitting(false);
    if (data) {
      setResult(data);
      setPhase("result");
      if (data.day_status) toast(data.day_status.message, "success", 6500);
    } else {
      toast(errorMessage(err), "error");
      if (response.status === 410) load();
    }
  }

  if (phase === "loading") return <p className="py-20 text-center text-muted">Preparing questions…</p>;

  if (phase === "error") {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="callout callout-bad" role="alert">{error}</div>
        <Link href={base} className="btn btn-secondary mt-4">Back to course</Link>
      </div>
    );
  }

  if (phase === "intro" && quiz) {
    return (
      <div className="mx-auto max-w-2xl">
        <PageHeader
          eyebrow={isPre ? "Diagnostic" : kind === "topic" ? "Topic assessment" : "Quiz"}
          title={quiz.title}
          crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Course", to: base }, { label: isPre ? "Pre-test" : "Quiz" }]}
        />
        <div className="card card-pad space-y-5">
          <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
            <dt className="text-muted">Scope</dt><dd>{quiz.scope}</dd>
            <dt className="text-muted">Questions</dt><dd>{quiz.questions.length} multiple choice</dd>
            {!isPre && <><dt className="text-muted">Pass mark</dt><dd>{quiz.threshold}%</dd></>}
          </dl>
          {isPre ? (
            <div className="callout">
              <b>This is not graded.</b> The pre-test shows what you already know so your study plan can skip what
              you have mastered and spend more time where you need it. Answer honestly; guessing makes the plan less useful.
            </div>
          ) : (
            <div className="callout callout-crimson">
              Score at least <b>{quiz.threshold}%</b> to complete this step. If you score lower, the topic is rescheduled
              for later with extra remediation material and the rest of your plan is recalculated.
            </div>
          )}
          <div className="flex gap-3">
            <button type="button" className="btn btn-lg" onClick={() => setPhase("running")}>{isPre ? "Begin pre-test" : "Start quiz"}</button>
            <Link href={backTo} className="btn btn-secondary btn-lg">Not now</Link>
          </div>
        </div>
      </div>
    );
  }

  if (phase === "running" && quiz) {
    return (
      <>
        <div className="mx-auto max-w-2xl"><PageHeader title={quiz.title} /></div>
        <QuizRunner questions={quiz.questions} submitting={submitting} onSubmit={submit} />
      </>
    );
  }

  if (!result) return null;
  const tone = result.passed ? "ok" : "bad";
  const a = result.actions;
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader eyebrow={isPre ? "Pre-test complete" : "Results"} title={isPre ? "Your pre-test results" : result.title} />
      <div className="card card-pad flex flex-wrap items-center gap-6">
        <RingProgress value={result.score} size={112} stroke={9} tone={isPre ? "" : tone} />
        <div className="flex-1">
          {isPre && result.plan ? (
            <>
              <h2 className="text-2xl font-semibold">{result.correct} of {result.total} correct</h2>
              <p className="mt-1.5 text-muted">
                Your personalised plan covers {plural(result.plan.tasks, "task")} across {plural(result.plan.days, "day")} at{" "}
                {result.plan.minutes_per_day} minutes a day. Sub-topics you already know get a short confirmation quiz; the rest start with study.
              </p>
            </>
          ) : (
            <>
              <h2><span className={`badge ${result.passed ? "badge-ok" : "badge-bad"}`}>{result.passed ? "Passed" : "Below pass mark"}</span></h2>
              <p className="mt-2 text-muted">{result.correct} of {result.total} correct · pass mark {result.threshold}%</p>
              <div className="mt-3 max-w-xs"><MeterBar value={result.score} threshold={result.threshold} label="Score" /></div>
            </>
          )}
        </div>
      </div>

      {result.day_status && (
        <div className="callout callout-ok"><b>{result.day_status.message}</b><br />Nice work — that closes today’s plan.</div>
      )}
      {a?.failed && (
        <div className="callout callout-warn">
          <b>Your plan has been adjusted.</b>
          <ul className="mt-2 list-disc pl-5">
            {a.items.map((i) => <li key={i.title}>{i.title} — Day {i.day} ({relDay(i.date)})</li>)}
            <li>The remaining tasks were recalculated{a.shifted ? ` (${a.shifted} moved later)` : ""}.</li>
          </ul>
        </div>
      )}
      {result.by_subtopic.some((s) => s.promoted) && (
        <div className="callout callout-ok">
          <b>Level up:</b> {result.by_subtopic.filter((s) => s.promoted).map((s) => `${s.title} → ${s.level}`).join(", ")}.
        </div>
      )}

      <div className="card">
        <div className="card-head"><h3 className="text-lg font-semibold">{isPre ? "Starting point by sub-topic" : "By sub-topic"}</h3></div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>Sub-topic</th><th className="num">Correct</th><th className="num">Score</th><th className="num">{isPre ? "Starting mastery" : "Mastery"}</th><th>Level</th></tr></thead>
            <tbody>
              {result.by_subtopic.map((s) => (
                <tr key={s.subtopic_id}>
                  <td>{s.title}</td>
                  <td className="num">{s.correct}/{s.total}</td>
                  <td className="num">{Math.round(s.score)}%</td>
                  <td className="num">{!isPre && s.before != null && <>{Math.round(s.before)}% → </>}<b>{Math.round(s.after)}%</b></td>
                  <td className="capitalize">{s.level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3 className="text-lg font-semibold">Question review</h3>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowReview(!showReview)}>{showReview ? "Hide" : "Show"}</button>
        </div>
        {showReview && (
          <div className="card-body divide-y divide-line-soft">
            {result.review.map((r, n) => (
              <div key={r.id} className="py-3.5">
                <div className="text-sm text-muted">Question {n + 1} · {r.subtopic_title}</div>
                <p className="my-1 font-medium">{r.text}</p>
                {!r.correct && <div className="text-sm text-bad">Your answer: {r.chosen == null ? "No answer" : r.options[r.chosen] ?? "—"}</div>}
                <div className="text-sm text-ok">Correct answer: {r.options[r.answer]}</div>
                <p className="mt-1.5 text-sm text-muted">{r.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {isPre && <Link href={`${base}/plan`} className="btn btn-lg">View my study plan</Link>}
        {!isPre && result.next_task && <Link href={taskHref(courseId, result.next_task)} className="btn btn-lg">Next: {result.next_task.title}</Link>}
        {!isPre && <Link href={`${base}/plan`} className="btn btn-secondary btn-lg">Study plan</Link>}
        {!isPre && subtopicId && <Link href={backTo} className="btn btn-secondary btn-lg">Back to sub-topic</Link>}
        {!isPre && <Link href={base} className="btn btn-secondary btn-lg">Course</Link>}
        {!isPre && result.next_task && <span className="text-sm text-muted">{TASK_LABEL[result.next_task.type]} · {relDay(result.next_task.date)}</span>}
      </div>
    </div>
  );
}
