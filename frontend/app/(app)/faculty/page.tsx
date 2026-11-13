import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "My courses" };

export default async function FacultyHome() {
  const api = await serverApi();
  const [courses, health] = await Promise.all([
    api.GET("/api/v1/faculty/courses").then(unwrap),
    api.GET("/api/v1/faculty/ai/health").then((r) => r.data),
  ]);
  return (
    <>
      <PageHeader
        eyebrow="Faculty portal"
        title="My courses"
        lede="Upload a syllabus and the AI drafts the topics, summaries, flashcards and quizzes. You review and edit everything before students see it."
        actions={<Link href="/faculty/new" className={buttonVariants()}>New course from syllabus</Link>}
      />
      {health && !health.ok && (
        <Card role="status" style={{ borderLeftColor: "var(--warning)" }} className="block gap-0 py-0 mb-5 border-l-4 px-4 py-3 text-sm">
          The AI model server is not reachable right now, so generating content will fail until it is back.
          You can still write and edit courses by hand.
        </Card>
      )}
      {courses.length === 0 ? (
        <Card className="gap-0 py-0 empty">
          <h3>No courses yet</h3>
          <p>Start from a syllabus (PDF, Word, a scan or pasted text).</p>
          <Link href="/faculty/new" className={buttonVariants()}>Upload a syllabus</Link>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {courses.map((c) => (
            <Card key={c.id} className="gap-0 p-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{c.code}</p>
                  <h2 className="mt-1 text-xl font-semibold">{c.title}</h2>
                </div>
                <Badge variant={c.status === "published" ? "success" : "warning"}>
                  {c.status === "published" ? "Published" : "Draft"}
                </Badge>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {c.topic_count} topics · {c.subtopic_count} sub-topics · {c.enrolled} enrolled · pass mark {c.threshold}%
              </p>
              <div className="mt-4">
                <Link href={`/faculty/courses/${c.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>Review and edit →</Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
