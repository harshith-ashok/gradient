"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { components } from "@/lib/api-client/schema";
import { STATUS_LABEL, STATUS_TONE } from "@/lib/format";

type Course = components["schemas"]["PracticeCourse"];

export function PracticeSearch({ courses }: { courses: Course[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const q = query.toLowerCase().replace(/^quiz me on\s*/, "").trim();
    return courses
      .map((c) => ({ ...c, subtopics: c.subtopics.filter((s) => !q || `${s.title} ${s.topic}`.toLowerCase().includes(q)) }))
      .filter((c) => c.subtopics.length);
  }, [courses, query]);
  const first = groups[0] && { course: groups[0].course_id, sub: groups[0].subtopics[0].id };
  const start = (courseId: string, sid: string) =>
    router.push(`/student/courses/${courseId}/quiz?kind=practice&subtopicId=${sid}`);

  return (
    <>
      <form className="card card-pad mb-6 flex gap-3" onSubmit={(e) => { e.preventDefault(); if (first) start(first.course, first.sub); }}>
        <label htmlFor="q" className="sr-only">Search sub-topics</label>
        <input
          id="q" className="input" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Quiz me on… (e.g. pointers, elasticity, inheritance)" autoComplete="off"
        />
        <button type="submit" className="btn" disabled={!first}>Start quiz</button>
      </form>
      {!groups.length && <div className="card empty">No sub-topic matches “{query}”.</div>}
      <div className="space-y-5">
        {groups.map((c) => (
          <section key={c.course_id} className="card">
            <div className="card-head"><h3 className="text-lg font-semibold">{c.code} · {c.title}</h3><span className="text-xs text-muted">{c.subtopics.length} sub-topics</span></div>
            <ul>
              {c.subtopics.map((s) => (
                <li key={s.id} className="flex items-center gap-3 border-b border-line-soft px-6 py-3 last:border-0">
                  <div className="flex-1"><div className="font-medium">{s.title}</div><div className="text-xs text-muted">{s.topic}</div></div>
                  <span className={`badge ${STATUS_TONE[s.status]}`}>{STATUS_LABEL[s.status]}</span>
                  <span className="w-10 text-right text-sm tabular-nums">{s.mastery}%</span>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => start(c.course_id, s.id)}>Quiz me</button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}
