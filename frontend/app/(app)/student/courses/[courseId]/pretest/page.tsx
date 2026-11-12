import type { Metadata } from "next";
import { QuizSession } from "@/components/QuizSession";

export const metadata: Metadata = { title: "Pre-test" };

export default async function PretestPage({ params }: PageProps<"/student/courses/[courseId]/pretest">) {
  const { courseId } = await params;
  return <QuizSession courseId={courseId} kind="pretest" />;
}
