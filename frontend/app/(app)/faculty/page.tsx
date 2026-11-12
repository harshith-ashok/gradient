import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";

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
        actions={<Link href="/faculty/new" className="btn btn-crimson">New course from syllabus</Link>}
      />
      {health && !health.ok && (
        <div className="card mb-5 border-l-4 px-4 py-3 text-sm" role="status" style={{ borderLeftColor: "var(--warn)" }}>
          The AI model server is not reachable right now, so generating content will fail until it is back.
          You can still write and edit courses by hand.
        </div>
      )}
      {courses.length === 0 ? (
        <div className="card empty">
          <h3>No courses yet</h3>
          <p>Start from a syllabus (PDF, Word, a scan or pasted text).</p>
          <Link href="/faculty/new" className="btn">Upload a syllabus</Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {courses.map((c) => (
            <article key={c.id} className="card card-pad">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{c.code}</p>
                  <h2 className="mt-1 text-xl font-semibold">{c.title}</h2>
                </div>
                <span className={`badge ${c.status === "published" ? "badge-ok" : "badge-warn"}`}>
                  {c.status === "published" ? "Published" : "Draft"}
                </span>
              </div>
              <p className="mt-3 text-sm text-muted">
                {c.topic_count} topics · {c.subtopic_count} sub-topics · {c.enrolled} enrolled · pass mark {c.threshold}%
              </p>
              <div className="mt-4">
                <Link href={`/faculty/courses/${c.id}`} className="btn btn-secondary btn-sm">Review and edit →</Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
