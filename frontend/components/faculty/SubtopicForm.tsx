"use client";

import { useState } from "react";
import { LEVELS, type Subtopic } from "./CourseEditor";

type Level = (typeof LEVELS)[number];
type Q = Subtopic["questions"][number];
const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
const paras = (s: string) => s.split(/\n\s*\n/).map((x) => x.trim()).filter(Boolean);
const Field = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
  <label className="block space-y-1.5 text-sm"><span className="font-medium">{label}</span>{children}{hint && <span className="block text-xs text-muted">{hint}</span>}</label>
);

export function SubtopicForm({ sub, running, onChange, onGenerate, onMove, onDelete }: {
  sub: Subtopic; running: boolean; onChange: (fn: (s: Subtopic) => void) => void;
  onGenerate: () => void; onMove: (d: number) => void; onDelete: () => void;
}) {
  const [level, setLevel] = useState<Level>("beginner");
  const [qLevel, setQLevel] = useState<Level | "all">("all");
  const shown = sub.questions.map((q, i) => ({ q, i })).filter(({ q }) => qLevel === "all" || q.level === qLevel);
  const summaryText = (l: Level) => (sub.summaries?.[l] ?? (l === "beginner" ? sub.summary : []) ?? []).join("\n\n");
  const setQ = (i: number, fn: (q: Q) => void) => onChange((s) => fn(s.questions[i]));

  return (
    <div className="space-y-4">
      <div className="card card-pad space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="mr-auto text-xl font-semibold">Sub-topic</h2>
          <button className="btn btn-secondary btn-sm" disabled={running} onClick={onGenerate}>Generate for this sub-topic</button>
          <button className="btn btn-secondary btn-sm" onClick={() => onMove(-1)} aria-label="Move up">↑</button>
          <button className="btn btn-secondary btn-sm" onClick={() => onMove(1)} aria-label="Move down">↓</button>
          <button className="btn btn-secondary btn-sm" onClick={onDelete}>Delete</button>
        </div>
        <Field label="Title"><input className="input" value={sub.title} onChange={(e) => onChange((s) => { s.title = e.target.value; })} /></Field>
        <Field label="Description"><input className="input" value={sub.description} onChange={(e) => onChange((s) => { s.description = e.target.value; })} /></Field>
        <Field label="Key points" hint="One per line. The AI covers these when it writes the material.">
          <textarea className="input" rows={4} defaultValue={sub.points.join("\n")} onBlur={(e) => onChange((s) => { s.points = lines(e.target.value); })} />
        </Field>
      </div>

      <div className="card card-pad space-y-3">
        <h3 className="text-lg font-semibold">Summaries by level</h3>
        <p className="text-sm text-muted">Each student reads the one that matches their level for this sub-topic. Separate paragraphs with a blank line.</p>
        <div role="tablist" className="flex flex-wrap gap-1 border-b border-line">
          {LEVELS.map((l) => (
            <button key={l} role="tab" aria-selected={level === l} onClick={() => setLevel(l)}
              className="-mb-px border-b-2 border-transparent px-3 py-2 text-sm font-medium capitalize text-muted aria-selected:border-crimson aria-selected:text-crimson">
              {l}{summaryText(l) ? "" : " ·  empty"}
            </button>
          ))}
        </div>
        <textarea key={level} className="input" rows={9} defaultValue={summaryText(level)}
          onBlur={(e) => onChange((s) => { s.summaries = { ...s.summaries, [level]: paras(e.target.value) }; if (level === "beginner") s.summary = paras(e.target.value); })} />
      </div>

      <div className="card card-pad space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Flashcards ({sub.flashcards.length})</h3>
          <button className="btn btn-secondary btn-sm" onClick={() => onChange((s) => { s.flashcards.push({ front: "", back: "", level: "beginner" }); })}>+ Card</button>
        </div>
        {sub.flashcards.map((f, i) => (
          <div key={i} className="grid gap-2 rounded border border-line-soft p-3 sm:grid-cols-[1fr_1fr_auto]">
            <textarea aria-label="Front" className="input" rows={2} placeholder="Front" value={f.front} onChange={(e) => onChange((s) => { s.flashcards[i].front = e.target.value; })} />
            <textarea aria-label="Back" className="input" rows={2} placeholder="Back" value={f.back} onChange={(e) => onChange((s) => { s.flashcards[i].back = e.target.value; })} />
            <div className="flex gap-2 sm:flex-col">
              <select aria-label="Card level" className="input !w-auto capitalize" value={f.level} onChange={(e) => onChange((s) => { s.flashcards[i].level = e.target.value as Level; })}>
                {LEVELS.map((l) => <option key={l}>{l}</option>)}
              </select>
              <button className="btn btn-secondary btn-sm" onClick={() => onChange((s) => { s.flashcards.splice(i, 1); })}>Remove</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-auto text-lg font-semibold">Quiz questions ({sub.questions.length})</h3>
          <select aria-label="Filter by level" className="input !w-auto capitalize" value={qLevel} onChange={(e) => setQLevel(e.target.value as Level | "all")}>
            <option value="all">All levels</option>{LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={() => onChange((s) => { s.questions.push({ level: qLevel === "all" ? "beginner" : qLevel, text: "", options: ["", "", "", ""], answer_index: 0, explanation: "" }); })}>+ Question</button>
        </div>
        {shown.length === 0 && <p className="text-sm text-muted">No questions at this level yet.</p>}
        {shown.map(({ q, i }) => (
          <fieldset key={q.id ?? i} className="space-y-2 rounded border border-line-soft p-3">
            <div className="flex gap-2">
              <textarea aria-label={`Question ${i + 1}`} className="input" rows={2} placeholder="Question" value={q.text} onChange={(e) => setQ(i, (x) => { x.text = e.target.value; })} />
              <div className="flex flex-col gap-2">
                <select aria-label="Question level" className="input !w-auto capitalize" value={q.level} onChange={(e) => setQ(i, (x) => { x.level = e.target.value as Level; })}>
                  {LEVELS.map((l) => <option key={l}>{l}</option>)}
                </select>
                <button className="btn btn-secondary btn-sm" onClick={() => onChange((s) => { s.questions.splice(i, 1); })}>Remove</button>
              </div>
            </div>
            {q.options.map((o, oi) => (
              <div key={oi} className="flex items-center gap-2">
                <input type="radio" name={`ans-${i}`} aria-label={`Option ${oi + 1} is correct`} checked={q.answer_index === oi} onChange={() => setQ(i, (x) => { x.answer_index = oi; })} />
                <input aria-label={`Option ${oi + 1}`} className="input" value={o} onChange={(e) => setQ(i, (x) => { x.options[oi] = e.target.value; })} />
              </div>
            ))}
            <input aria-label="Explanation" className="input" placeholder="Why the correct option is right" value={q.explanation} onChange={(e) => setQ(i, (x) => { x.explanation = e.target.value; })} />
          </fieldset>
        ))}
      </div>

      <div className="card card-pad space-y-3">
        <h3 className="text-lg font-semibold">Remediation</h3>
        <p className="text-sm text-muted">Shown to a student who fails this sub-topic&apos;s quiz.</p>
        <Field label="Explanation (a different angle)">
          <textarea className="input" rows={3} value={sub.remediation?.explanation ?? ""}
            onChange={(e) => onChange((s) => { s.remediation = { explanation: e.target.value, steps: s.remediation?.steps ?? [] }; })} />
        </Field>
        <Field label="Practice steps" hint="One per line.">
          <textarea className="input" rows={3} defaultValue={(sub.remediation?.steps ?? []).join("\n")}
            onBlur={(e) => onChange((s) => { s.remediation = { explanation: s.remediation?.explanation ?? "", steps: lines(e.target.value) }; })} />
        </Field>
      </div>
    </div>
  );
}
