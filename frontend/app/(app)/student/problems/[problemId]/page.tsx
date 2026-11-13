import type { Metadata } from "next";
import { ProblemSolver } from "@/components/coding/ProblemSolver";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";

type Props = PageProps<"/student/problems/[problemId]">;

async function load(problemId: string) {
  const api = await serverApi();
  const [problem, history] = await Promise.all([
    api.GET("/api/v1/student/problems/{problem_id}", { params: { path: { problem_id: problemId } } }),
    api.GET("/api/v1/student/problems/{problem_id}/submissions", { params: { path: { problem_id: problemId } } }),
  ]);
  return { problem: unwrap(problem), history: unwrap(history) };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { problemId } = await params;
  return { title: (await load(problemId)).problem.title };
}

export default async function ProblemPage({ params }: Props) {
  const { problemId } = await params;
  const { problem, history } = await load(problemId);
  const base = `/student/courses/${problem.course_id}`;
  return (
    <>
      <PageHeader
        crumbs={[
          { label: "Courses", to: "/student/courses" },
          { label: problem.course_code, to: base },
          { label: problem.subtopic_title, to: `${base}/subtopics/${problem.subtopic_id}` },
          { label: "Coding challenge" },
        ]}
        eyebrow="Coding challenge"
        title={problem.title}
      />
      <ProblemSolver problem={problem} history={history} />
    </>
  );
}
