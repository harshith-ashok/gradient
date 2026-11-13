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
import { Rich } from "./Rich";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

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

  if (phase === "loading") return <p className="py-20 text-center text-muted-foreground">Preparing questions…</p>;

  if (phase === "error") {
    return (
      <div className="mx-auto max-w-2xl">
        <Alert role="alert" className="border-destructive/30 bg-destructive/10 text-destructive">{error}</Alert>
        <Link href={base} className={cn(buttonVariants({ variant: "outline" }), "mt-4")}>Back to course</Link>
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
        <Card className="gap-0 p-6 space-y-5">
          <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
            <dt className="text-muted-foreground">Scope</dt><dd>{quiz.scope}</dd>
            <dt className="text-muted-foreground">Questions</dt><dd>{quiz.questions.length} multiple choice</dd>
            {!isPre && <><dt className="text-muted-foreground">Pass mark</dt><dd>{quiz.threshold}%</dd></>}
          </dl>
          {isPre ? (
            <Alert className="bg-muted/50">
              <b>This is not graded.</b> The pre-test shows what you already know so your study plan can skip what
              you have mastered and spend more time where you need it. Answer honestly; guessing makes the plan less useful.
            </Alert>
          ) : (
            <Alert className="bg-muted">
              Score at least <b>{quiz.threshold}%</b> to complete this step. If you score lower, the topic is rescheduled
              for later with extra remediation material and the rest of your plan is recalculated.
            </Alert>
          )}
          <div className="flex gap-3">
            <Button type="button" onClick={() => setPhase("running")} size="lg">{isPre ? "Begin pre-test" : "Start quiz"}</Button>
            <Link href={backTo} className={buttonVariants({ variant: "outline", size: "lg" })}>Not now</Link>
          </div>
        </Card>
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
      <Card className="gap-0 p-6 flex flex-wrap items-center gap-6">
        <RingProgress value={result.score} size={112} stroke={9} tone={isPre ? "" : tone} />
        <div className="flex-1">
          {isPre && result.plan ? (
            <>
              <h2 className="text-2xl font-semibold">{result.correct} of {result.total} correct</h2>
              <p className="mt-1.5 text-muted-foreground">
                Your personalised plan covers {plural(result.plan.tasks, "task")} across {plural(result.plan.days, "day")} at{" "}
                {result.plan.minutes_per_day} minutes a day. Sub-topics you already know get a short confirmation quiz; the rest start with study.
              </p>
            </>
          ) : (
            <>
              <h2><Badge variant={result.passed ? "success" : "destructive"}>{result.passed ? "Passed" : "Below pass mark"}</Badge></h2>
              <p className="mt-2 text-muted-foreground">{result.correct} of {result.total} correct · pass mark {result.threshold}%</p>
              <div className="mt-3 max-w-xs"><MeterBar value={result.score} threshold={result.threshold} label="Score" /></div>
            </>
          )}
        </div>
      </Card>

      {result.day_status && (
        <Alert className="border-success/30 bg-success/10 text-success"><b>{result.day_status.message}</b><br />Nice work — that closes today’s plan.</Alert>
      )}
      {a?.failed && (
        <Alert className="border-warning/30 bg-warning/10 text-warning">
          <b>Your plan has been adjusted.</b>
          <ul className="mt-2 list-disc pl-5">
            {a.items.map((i) => <li key={i.title}>{i.title} — Day {i.day} ({relDay(i.date)})</li>)}
            <li>The remaining tasks were recalculated{a.shifted ? ` (${a.shifted} moved later)` : ""}.</li>
          </ul>
        </Alert>
      )}
      {result.by_subtopic.some((s) => s.promoted) && (
        <Alert className="border-success/30 bg-success/10 text-success">
          <b>Level up:</b> {result.by_subtopic.filter((s) => s.promoted).map((s) => `${s.title} → ${s.level}`).join(", ")}.
        </Alert>
      )}

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">{isPre ? "Starting point by sub-topic" : "By sub-topic"}</h3></div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Sub-topic</TableHead><TableHead className="text-right tabular-nums">Correct</TableHead><TableHead className="text-right tabular-nums">Score</TableHead><TableHead className="text-right tabular-nums">{isPre ? "Starting mastery" : "Mastery"}</TableHead><TableHead>Level</TableHead></TableRow></TableHeader>
            <TableBody>
              {result.by_subtopic.map((s) => (
                <TableRow key={s.subtopic_id}>
                  <TableCell>{s.title}</TableCell>
                  <TableCell className="text-right tabular-nums">{s.correct}/{s.total}</TableCell>
                  <TableCell className="text-right tabular-nums">{Math.round(s.score)}%</TableCell>
                  <TableCell className="text-right tabular-nums">{!isPre && s.before != null && <>{Math.round(s.before)}% → </>}<b>{Math.round(s.after)}%</b></TableCell>
                  <TableCell className="capitalize">{s.level}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="gap-0 py-0">
        <div className="flex items-center justify-between gap-4 border-b px-6 py-4">
          <h3 className="text-lg font-semibold">Question review</h3>
          <Button type="button" onClick={() => setShowReview(!showReview)} variant="outline" size="sm">{showReview ? "Hide" : "Show"}</Button>
        </div>
        {showReview && (
          <div className="px-6 py-4 divide-y divide-border">
            {result.review.map((r, n) => (
              <div key={r.id} className="py-3.5">
                <div className="text-sm text-muted-foreground">Question {n + 1} · {r.subtopic_title}</div>
                <div className="my-1 font-medium"><Rich>{r.text}</Rich></div>
                {!r.correct && <div className="text-sm text-destructive">Your answer: {r.chosen == null ? "No answer" : <Rich inline>{r.options[r.chosen] ?? "—"}</Rich>}</div>}
                <div className="text-sm text-success">Correct answer: <Rich inline>{r.options[r.answer]}</Rich></div>
                <div className="mt-1.5 text-sm text-muted-foreground"><Rich>{r.explanation}</Rich></div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        {isPre && <Link href={`${base}/plan`} className={buttonVariants({ size: "lg" })}>View my study plan</Link>}
        {!isPre && result.next_task && <Link href={taskHref(courseId, result.next_task)} className={buttonVariants({ size: "lg" })}>Next: {result.next_task.title}</Link>}
        {!isPre && <Link href={`${base}/plan`} className={buttonVariants({ variant: "outline", size: "lg" })}>Study plan</Link>}
        {!isPre && subtopicId && <Link href={backTo} className={buttonVariants({ variant: "outline", size: "lg" })}>Back to sub-topic</Link>}
        {!isPre && <Link href={base} className={buttonVariants({ variant: "outline", size: "lg" })}>Course</Link>}
        {!isPre && result.next_task && <span className="text-sm text-muted-foreground">{TASK_LABEL[result.next_task.type]} · {relDay(result.next_task.date)}</span>}
      </div>
    </div>
  );
}
