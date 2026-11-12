import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Courses" };

export default async function CatalogPage() {
  const api = await serverApi();
  const courses = unwrap(await api.GET("/api/v1/student/catalog"));

  return (
    <>
      <PageHeader
        eyebrow="Course catalogue"
        title="Choose a course"
        lede="Enrol in a course, take a short pre-test, and receive a study plan built around what you already know."
      />
      {courses.length === 0 ? (
        <p className="rounded-md border border-line bg-surface p-8 text-center text-muted">
          No courses are published yet.
        </p>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {courses.map((c) => (
            <article
              key={c.id}
              style={{ borderTopColor: c.accent ?? "var(--crimson)" }}
              className="flex flex-col justify-between rounded-md border border-line border-t-4 bg-surface p-6"
            >
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted">
                  {c.code} · {c.department}
                </p>
                <h3 className="mt-1.5 text-2xl font-semibold">{c.title}</h3>
                <p className="mt-2 text-sm text-muted">{c.description}</p>
                <p className="mt-3 flex flex-wrap gap-x-4 text-xs text-muted">
                  <span>{c.topic_count} topics</span>
                  <span>{c.subtopic_count} sub-topics</span>
                  <span>{c.credits} credits</span>
                  <span>{c.instructor}</span>
                </p>
              </div>
              <div className="mt-5 flex items-center justify-between gap-3">
                {c.enrollment ? (
                  <span className="badge badge-ok">Enrolled · {c.enrollment.overall}%</span>
                ) : (
                  <span className="text-sm text-muted">{c.level}</span>
                )}
                <div className="flex gap-2">
                  <Link href={`/student/courses/${c.id}`} className="btn btn-secondary btn-sm">
                    {c.enrollment ? "Open" : "View topics"}
                  </Link>
                  {!c.enrollment && (
                    <Link href={`/student/courses/${c.id}/pretest`} className="btn btn-sm">Enrol</Link>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
