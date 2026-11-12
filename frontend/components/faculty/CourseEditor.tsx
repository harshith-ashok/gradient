"use client";

import { useCallback, useMemo, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { useToast } from "../Toast";
import { QuestionSheets } from "./QuestionSheets";
import { SubtopicForm } from "./SubtopicForm";
import { stepText, useJob } from "./useJob";

export type Course = components["schemas"]["CourseFull"];
export type Topic = Course["topics"][number];
export type Subtopic = Topic["subtopics"][number];
export const LEVELS = ["beginner", "intermediate", "advanced", "expert"] as const;

const blankSub = (): Subtopic => ({
  title: "New sub-topic", description: "", points: [], summary: [], summaries: {}, flashcards: [], questions: [], remediation: null,
});

function move<T>(arr: T[], i: number, d: number): T[] {
  const j = i + d;
  if (j < 0 || j >= arr.length) return arr;
  const out = [...arr];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

export function CourseEditor({ initial, isNew }: { initial: Course; isNew: boolean }) {
  const toast = useToast();
  const [course, setCourse] = useState(initial);
  const [dirty, setDirty] = useState(false);
  const [sel, setSel] = useState<{ t: number; s: number | null }>({ t: 0, s: initial.topics[0]?.subtopics.length ? 0 : null });
  const [saving, setSaving] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [force, setForce] = useState(false);

  const reload = useCallback(async () => {
    const { data } = await api.GET("/api/v1/faculty/courses/{course_id}", { params: { path: { course_id: initial.id } } });
    if (data) { setCourse(data); setDirty(false); }
  }, [initial.id]);

  const job = useJob(jobId, (j) => {
    setJobId(null);
    if (j.status === "failed") return toast(j.error ?? "Generation failed.", "error");
    const failed = ((j.result as { failed?: unknown[] } | null)?.failed ?? []).length;
    toast(failed ? `Generated, but ${failed} sub-topic(s) failed. Run it again for those.` : "Study material generated. Review it below.", failed ? "error" : "success");
    reload();
  });
  const running = !!jobId;

  const edit = (fn: (c: Course) => void) => {
    setCourse((prev) => { const next = structuredClone(prev); fn(next); return next; });
    setDirty(true);
  };

  async function save(): Promise<boolean> {
    setSaving(true);
    const { data, error } = await api.PUT("/api/v1/faculty/courses/{course_id}", {
      params: { path: { course_id: course.id } }, body: course,
    });
    setSaving(false);
    if (error || !data) { toast(errorMessage(error), "error"); return false; }
    setCourse(data);
    setDirty(false);
    toast("Saved.", "success");
    return true;
  }

  async function generate(subtopicIds: string[] | null) {
    if (dirty && !(await save())) return;
    const { data, error } = await api.POST("/api/v1/faculty/courses/{course_id}/generate", {
      params: { path: { course_id: course.id } }, body: { subtopic_ids: subtopicIds, force },
    });
    if (error || !data) return toast(errorMessage(error), "error");
    setJobId(data.job_id);
  }

  async function setStatus(status: "draft" | "published") {
    if (dirty && !(await save())) return;
    const { error } = await api.POST("/api/v1/faculty/courses/{course_id}/status", {
      params: { path: { course_id: course.id } }, body: { status },
    });
    if (error) return toast(errorMessage(error), "error");
    setCourse((c) => ({ ...c, status }));
    toast(status === "published" ? "Published. Students can now enrol." : "Moved back to draft.", "success");
  }

  const topic = course.topics[sel.t];
  const sub = sel.s !== null ? topic?.subtopics[sel.s] : undefined;
  const gaps = useMemo(
    () => course.topics.flatMap((t) => t.subtopics).filter((s) => LEVELS.some((l) => !(s.summaries?.[l]?.length) && !(l === "beginner" && s.summary.length)) || s.questions.length < 4).length,
    [course],
  );

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="card lg:sticky lg:top-4">
        <div className="card-head !py-3">
          <span className={`badge ${course.status === "published" ? "badge-ok" : "badge-warn"}`}>
            {course.status === "published" ? "Published" : "Draft"}
          </span>
          <button className="btn btn-sm btn-secondary" onClick={() => edit((c) => { c.topics.push({ title: "New topic", summary: "", subtopics: [] }); setSel({ t: c.topics.length - 1, s: null }); })}>
            + Topic
          </button>
        </div>
        <nav aria-label="Course outline" className="max-h-[60vh] overflow-y-auto py-1">
          {course.topics.map((t, ti) => (
            <div key={t.id ?? ti}>
              <button className={`block w-full px-5 py-2 text-left text-sm font-semibold hover:bg-ink-50 ${sel.t === ti && sel.s === null ? "text-crimson" : ""}`}
                onClick={() => setSel({ t: ti, s: null })}>{t.title || "Untitled topic"}</button>
              {t.subtopics.map((s, si) => {
                const levels = LEVELS.filter((l) => s.summaries?.[l]?.length || (l === "beginner" && s.summary.length)).length;
                return (
                  <button key={s.id ?? si} onClick={() => setSel({ t: ti, s: si })} aria-current={sel.t === ti && sel.s === si}
                    className="flex w-full items-center justify-between gap-2 py-1.5 pl-9 pr-4 text-left text-sm hover:bg-ink-50 aria-[current=true]:bg-crimson-soft aria-[current=true]:text-crimson">
                    <span className="truncate">{s.title || "Untitled"}</span>
                    <span className={`badge ${levels === 4 && s.questions.length >= 4 ? "badge-ok" : "badge-warn"}`} title={`${levels} of 4 summary levels, ${s.questions.length} questions`}>
                      {levels}/4
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      <section className="min-w-0 space-y-4">
        {isNew && course.status === "draft" && (
          <div className="card card-pad text-sm">
            The outline is ready. Next, ask the AI to write the summaries, flashcards and quiz questions, then review them.
          </div>
        )}
        <div className="card card-pad flex flex-wrap items-center gap-3">
          <button className="btn btn-crimson" disabled={running} onClick={() => generate(null)}>
            {running ? "Generating…" : "Generate study material for the whole course"}
          </button>
          <label className="flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
            Replace what is already written
          </label>
          <span className="flex-1" />
          <button className="btn btn-secondary" disabled={!dirty || saving} onClick={save}>{saving ? "Saving…" : dirty ? "Save changes" : "Saved"}</button>
          {course.status === "published"
            ? <button className="btn btn-secondary" onClick={() => setStatus("draft")}>Unpublish</button>
            : <button className="btn" onClick={() => setStatus("published")}>Publish</button>}
        </div>
        <QuestionSheets
          courseId={course.id} code={course.code} dirty={dirty} onSaveFirst={save} onImported={reload}
        />
        {running && (
          <div className="card card-pad text-sm" role="status" aria-live="polite">
            <p className="font-medium">Writing study material</p>
            <p className="text-muted">{stepText(job, "Starting…")}</p>
          </div>
        )}
        {course.status === "draft" && gaps > 0 && (
          <p className="text-sm text-muted">{gaps} {gaps === 1 ? "sub-topic still lacks" : "sub-topics still lack"} summaries at some level or fewer than 4 questions. Students can still use them, but generate or write the rest first.</p>
        )}

        {sub && sel.s !== null ? (
          <SubtopicForm
            key={sub.id ?? `${sel.t}-${sel.s}`} sub={sub} running={running}
            onChange={(fn) => edit((c) => fn(c.topics[sel.t].subtopics[sel.s!]))}
            onGenerate={() => sub.id ? generate([sub.id]) : toast("Save the course first.", "error")}
            onMove={(d) => { edit((c) => { c.topics[sel.t].subtopics = move(c.topics[sel.t].subtopics, sel.s!, d); }); setSel({ t: sel.t, s: sel.s! + d }); }}
            onDelete={() => { if (confirm(`Delete “${sub.title}”? Students' history for it is kept, but its content is removed.`)) { edit((c) => { c.topics[sel.t].subtopics.splice(sel.s!, 1); }); setSel({ t: sel.t, s: null }); } }}
          />
        ) : topic ? (
          <div className="card card-pad space-y-4">
            <label className="block space-y-1.5 text-sm"><span className="font-medium">Topic title</span>
              <input className="input" value={topic.title} onChange={(e) => edit((c) => { c.topics[sel.t].title = e.target.value; })} /></label>
            <label className="block space-y-1.5 text-sm"><span className="font-medium">Topic summary</span>
              <textarea className="input" rows={3} value={topic.summary} onChange={(e) => edit((c) => { c.topics[sel.t].summary = e.target.value; })} /></label>
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-secondary btn-sm" onClick={() => edit((c) => { c.topics[sel.t].subtopics.push(blankSub()); setSel({ t: sel.t, s: c.topics[sel.t].subtopics.length - 1 }); })}>+ Sub-topic</button>
              <button className="btn btn-secondary btn-sm" disabled={sel.t === 0} onClick={() => { edit((c) => { c.topics = move(c.topics, sel.t, -1); }); setSel({ t: sel.t - 1, s: null }); }}>Move up</button>
              <button className="btn btn-secondary btn-sm" disabled={sel.t === course.topics.length - 1} onClick={() => { edit((c) => { c.topics = move(c.topics, sel.t, 1); }); setSel({ t: sel.t + 1, s: null }); }}>Move down</button>
              <button className="btn btn-secondary btn-sm" onClick={() => { if (confirm(`Delete the topic “${topic.title}” and everything in it?`)) { edit((c) => { c.topics.splice(sel.t, 1); }); setSel({ t: 0, s: null }); } }}>Delete topic</button>
            </div>
          </div>
        ) : (
          <div className="card empty"><h3>No topics yet</h3><p>Add a topic from the sidebar.</p></div>
        )}
      </section>
    </div>
  );
}
