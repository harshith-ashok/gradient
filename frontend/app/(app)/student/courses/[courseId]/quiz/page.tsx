import type { Metadata } from "next";
import { QuizSession } from "@/components/QuizSession";

export const metadata: Metadata = { title: "Quiz" };

const KINDS = ["topic", "subtopic", "practice"] as const;

export default async function QuizPage({ params, searchParams }: PageProps<"/student/courses/[courseId]/quiz">) {
  const { courseId } = await params;
  const q = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);
  const kind = KINDS.find((k) => k === q.kind) ?? "subtopic";
  const topicId = one(q.topicId);
  const subtopicId = one(q.subtopicId);
  // Re-key so opening a different quiz always starts a fresh session.
  return <QuizSession key={`${kind}|${topicId}|${subtopicId}`} courseId={courseId} kind={kind} topicId={topicId} subtopicId={subtopicId} />;
}
