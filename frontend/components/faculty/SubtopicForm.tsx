"use client";

import { useState } from "react";
import { LEVELS, type Subtopic } from "./CourseEditor";
import { Rich } from "../Rich";
import { CodingProblems } from "./CodingProblems";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";

type Level = (typeof LEVELS)[number];
type Q = Subtopic["questions"][number];
const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
const paras = (s: string) => s.split(/\n\s*\n/).map((x) => x.trim()).filter(Boolean);
const Field = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
  <label className="block space-y-1.5 text-sm"><span className="font-medium">{label}</span>{children}{hint && <span className="block text-xs text-muted-foreground">{hint}</span>}</label>
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
      <Card className="gap-0 p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="mr-auto text-xl font-semibold">Sub-topic</h2>
          <Button disabled={running} onClick={onGenerate} variant="outline" size="sm">Generate for this sub-topic</Button>
          <Button onClick={() => onMove(-1)} aria-label="Move up" variant="outline" size="sm">↑</Button>
          <Button onClick={() => onMove(1)} aria-label="Move down" variant="outline" size="sm">↓</Button>
          <Button onClick={onDelete} variant="outline" size="sm">Delete</Button>
        </div>
        <Field label="Title"><Input value={sub.title} onChange={(e) => onChange((s) => { s.title = e.target.value; })} /></Field>
        <Field label="Description"><Input value={sub.description} onChange={(e) => onChange((s) => { s.description = e.target.value; })} /></Field>
        <Field label="Key points" hint="One per line. The AI covers these when it writes the material.">
          <Textarea rows={4} defaultValue={sub.points.join("\n")} onBlur={(e) => onChange((s) => { s.points = lines(e.target.value); })} />
        </Field>
      </Card>

      <Card className="gap-0 p-6 space-y-3">
        <h3 className="text-lg font-semibold">Summaries by level</h3>
        <p className="text-sm text-muted-foreground">Each student reads the one that matches their level for this sub-topic. Separate paragraphs with a blank line.</p>
        <div role="tablist" className="flex flex-wrap gap-1 border-b border-border">
          {LEVELS.map((l) => (
            <button key={l} role="tab" aria-selected={level === l} onClick={() => setLevel(l)}
              className="-mb-px border-b-2 border-transparent px-3 py-2 text-sm font-medium capitalize text-muted-foreground aria-selected:border-primary aria-selected:text-primary">
              {l}{summaryText(l) ? "" : " ·  empty"}
            </button>
          ))}
        </div>
        <Textarea key={level} rows={9} defaultValue={summaryText(level)} onBlur={(e) => onChange((s) => { s.summaries = { ...s.summaries, [level]: paras(e.target.value) }; if (level === "beginner") s.summary = paras(e.target.value); })} />
      </Card>

      <Card className="gap-0 p-6 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Flashcards ({sub.flashcards.length})</h3>
          <Button onClick={() => onChange((s) => { s.flashcards.push({ front: "", back: "", level: "beginner" }); })} variant="outline" size="sm">+ Card</Button>
        </div>
        {sub.flashcards.map((f, i) => (
          <div key={i} className="grid gap-2 rounded border border-border p-3 sm:grid-cols-[1fr_1fr_auto]">
            <Textarea aria-label="Front" rows={2} placeholder="Front" value={f.front} onChange={(e) => onChange((s) => { s.flashcards[i].front = e.target.value; })} />
            <Textarea aria-label="Back" rows={2} placeholder="Back" value={f.back} onChange={(e) => onChange((s) => { s.flashcards[i].back = e.target.value; })} />
            <div className="flex gap-2 sm:flex-col">
              <NativeSelect aria-label="Card level" value={f.level} onChange={(e) => onChange((s) => { s.flashcards[i].level = e.target.value as Level; })} className="!w-auto capitalize">
                {LEVELS.map((l) => <option key={l}>{l}</option>)}
              </NativeSelect>
              <Button onClick={() => onChange((s) => { s.flashcards.splice(i, 1); })} variant="outline" size="sm">Remove</Button>
            </div>
          </div>
        ))}
      </Card>

      <Card className="gap-0 p-6 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-auto text-lg font-semibold">Quiz questions ({sub.questions.length})</h3>
          <NativeSelect aria-label="Filter by level" value={qLevel} onChange={(e) => setQLevel(e.target.value as Level | "all")} className="!w-auto capitalize">
            <option value="all">All levels</option>{LEVELS.map((l) => <option key={l}>{l}</option>)}
          </NativeSelect>
          <Button onClick={() => onChange((s) => { s.questions.push({ level: qLevel === "all" ? "beginner" : qLevel, text: "", options: ["", "", "", ""], answer_index: 0, explanation: "" }); })} variant="outline" size="sm">+ Question</Button>
        </div>
        {shown.length === 0 && <p className="text-sm text-muted-foreground">No questions at this level yet.</p>}
        {shown.map(({ q, i }) => (
          <fieldset key={q.id ?? i} className="space-y-2 rounded border border-border p-3">
            <div className="flex gap-2">
              <Textarea aria-label={`Question ${i + 1}`} rows={q.text.includes("\n") ? 6 : 2} placeholder="Question (Markdown: use ```c on its own line for code)" value={q.text} onChange={(e) => setQ(i, (x) => { x.text = e.target.value; })} className="font-mono text-[13px]" />
              <div className="flex flex-col gap-2">
                <NativeSelect aria-label="Question level" value={q.level} onChange={(e) => setQ(i, (x) => { x.level = e.target.value as Level; })} className="!w-auto capitalize">
                  {LEVELS.map((l) => <option key={l}>{l}</option>)}
                </NativeSelect>
                <Button onClick={() => onChange((s) => { s.questions.splice(i, 1); })} variant="outline" size="sm">Remove</Button>
              </div>
            </div>
            {q.options.map((o, oi) => (
              <div key={oi} className="flex items-center gap-2">
                <input type="radio" name={`ans-${i}`} aria-label={`Option ${oi + 1} is correct`} checked={q.answer_index === oi} onChange={() => setQ(i, (x) => { x.answer_index = oi; })} />
                <Input aria-label={`Option ${oi + 1}`} value={o} onChange={(e) => setQ(i, (x) => { x.options[oi] = e.target.value; })} />
              </div>
            ))}
            <Input aria-label="Explanation" placeholder="Why the correct option is right" value={q.explanation} onChange={(e) => setQ(i, (x) => { x.explanation = e.target.value; })} />
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground">Preview as a student sees it</summary>
              <div className="mt-2 space-y-2 rounded-md bg-muted p-3">
                <div className=" text-lg"><Rich>{q.text || "*(empty question)*"}</Rich></div>
                {q.options.map((o, oi) => (
                  <div key={oi} className={`flex gap-2 ${q.answer_index === oi ? "font-semibold text-success" : ""}`}>
                    <b>{"ABCDEFGHIJ"[oi]}</b><Rich inline>{o}</Rich>
                  </div>
                ))}
                {q.explanation && <div className="text-muted-foreground"><Rich>{q.explanation}</Rich></div>}
              </div>
            </details>
          </fieldset>
        ))}
      </Card>

      {sub.id ? <CodingProblems subtopicId={sub.id} /> : (
        <Card className="gap-0 p-6 text-sm text-muted-foreground">Save the course to add coding challenges to this sub-topic.</Card>
      )}

      <Card className="gap-0 p-6 space-y-3">
        <h3 className="text-lg font-semibold">Remediation</h3>
        <p className="text-sm text-muted-foreground">Shown to a student who fails this sub-topic&apos;s quiz.</p>
        <Field label="Explanation (a different angle)">
          <Textarea rows={3} value={sub.remediation?.explanation ?? ""} onChange={(e) => onChange((s) => { s.remediation = { explanation: e.target.value, steps: s.remediation?.steps ?? [] }; })} />
        </Field>
        <Field label="Practice steps" hint="One per line.">
          <Textarea rows={3} defaultValue={(sub.remediation?.steps ?? []).join("\n")} onBlur={(e) => onChange((s) => { s.remediation = { explanation: s.remediation?.explanation ?? "", steps: lines(e.target.value) }; })} />
        </Field>
      </Card>
    </div>
  );
}
