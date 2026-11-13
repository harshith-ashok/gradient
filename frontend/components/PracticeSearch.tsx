"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { components } from "@/lib/api-client/schema";
import { STATUS_LABEL, STATUS_TONE } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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
      <form onSubmit={(e) => { e.preventDefault(); if (first) start(first.course, first.sub); }} className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10 p-6 mb-6 flex gap-3">
        <label htmlFor="q" className="sr-only">Search sub-topics</label>
        <Input id="q" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Quiz me on… (e.g. pointers, elasticity, inheritance)" autoComplete="off" />
        <Button type="submit" disabled={!first}>Start quiz</Button>
      </form>
      {!groups.length && <Card className="gap-0 py-0 empty">No sub-topic matches “{query}”.</Card>}
      <div className="space-y-5">
        {groups.map((c) => (
          <Card key={c.course_id} className="gap-0 py-0">
            <div className="flex items-center justify-between gap-4 border-b px-6 py-4"><h3 className="text-lg font-semibold">{c.code} · {c.title}</h3><span className="text-xs text-muted-foreground">{c.subtopics.length} sub-topics</span></div>
            <ul>
              {c.subtopics.map((s) => (
                <li key={s.id} className="flex items-center gap-3 border-b border-border px-6 py-3 last:border-0">
                  <div className="flex-1"><div className="font-medium">{s.title}</div><div className="text-xs text-muted-foreground">{s.topic}</div></div>
                  <Badge variant={STATUS_TONE[s.status]}>{STATUS_LABEL[s.status]}</Badge>
                  <span className="w-10 text-right text-sm tabular-nums">{s.mastery}%</span>
                  <Button type="button" onClick={() => start(c.course_id, s.id)} variant="outline" size="sm">Quiz me</Button>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </>
  );
}
