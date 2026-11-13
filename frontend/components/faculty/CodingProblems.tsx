"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { Editor, LANG_LABEL, type Lang } from "../coding/Editor";
import { Results } from "../coding/Results";
import { useSubmission } from "../coding/useSubmission";
import { Rich } from "../Rich";
import { useToast } from "../Toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";

type Problem = components["schemas"]["ProblemFull"];
type Draft = Omit<Problem, "id" | "subtopic_id" | "position"> & { id?: string; uid: string };
const ALL: Lang[] = ["python", "c", "cpp"];
const LEVELS = ["beginner", "intermediate", "advanced", "expert"] as const;

const blank = (): Draft => ({
  uid: crypto.randomUUID(), title: "", statement: "", level: "beginner", languages: ["python", "c", "cpp"], starter: {},
  time_limit_ms: 2000, memory_mb: 256, tests: [{ input: "", expected: "", sample: true }, { input: "", expected: "", sample: false }],
});

export function CodingProblems({ subtopicId }: { subtopicId: string }) {
  const [problems, setProblems] = useState<Draft[] | null>(null);

  const reload = useCallback(async () => {
    const { data } = await api.GET("/api/v1/faculty/subtopics/{subtopic_id}/problems", { params: { path: { subtopic_id: subtopicId } } });
    setProblems((data ?? []).map((p) => ({ ...p, uid: p.id })));
  }, [subtopicId]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading from the server when the panel mounts
    void reload();
  }, [reload]);

  return (
    <Card className="gap-0 p-6 space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="mr-auto text-lg font-semibold">Coding challenges ({problems?.filter((p) => p.id).length ?? 0})</h3>
        <Button disabled={problems === null} onClick={() => setProblems([...(problems ?? []), blank()])} variant="outline" size="sm">+ Challenge</Button>
      </div>
      <p className="text-sm text-muted-foreground">
        LeetCode-style exercises. Students write a program that reads standard input and prints standard output; it runs
        against your tests in an isolated sandbox. Sample tests are shown to students, the rest stay hidden.
      </p>
      {problems === null && <p className="text-sm text-muted-foreground">Loading…</p>}
      {problems?.map((p) => (
        <ProblemEditor key={p.uid} initial={p} subtopicId={subtopicId}
          onSaved={(saved) => setProblems((all) => (all ?? []).map((x) => (x.uid === p.uid ? { ...saved, uid: p.uid } : x)))}
          onDiscard={() => setProblems((all) => (all ?? []).filter((x) => x.uid !== p.uid))} />
      ))}
    </Card>
  );
}

function ProblemEditor({ initial, subtopicId, onSaved, onDiscard }: {
  initial: Draft; subtopicId: string; onSaved: (saved: Problem) => void; onDiscard: () => void;
}) {
  const toast = useToast();
  const [d, setD] = useState<Draft>(initial);
  const [id, setId] = useState(initial.id);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(!initial.id);
  const [refLang, setRefLang] = useState<Lang>("python");
  const [ref, setRef] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const sub = useSubmission(runId, true, () => setRunning(false));
  const set = (patch: Partial<Draft>) => setD((x) => ({ ...x, ...patch }));
  const setTest = (i: number, patch: Partial<Draft["tests"][number]>) =>
    set({ tests: d.tests.map((t, j) => (j === i ? { ...t, ...patch } : t)) });

  async function save(): Promise<string | null> {
    setSaving(true);
    const body = { ...d, id: undefined, uid: undefined } as never;
    const res = id
      ? await api.PUT("/api/v1/faculty/problems/{problem_id}", { params: { path: { problem_id: id } }, body })
      : await api.POST("/api/v1/faculty/subtopics/{subtopic_id}/problems", { params: { path: { subtopic_id: subtopicId } }, body });
    setSaving(false);
    if (res.error || !res.data) { toast(errorMessage(res.error, "Check the title, statement, languages and that at least one test is a sample."), "error"); return null; }
    setId(res.data.id);
    onSaved(res.data);
    toast("Challenge saved.", "success");
    return res.data.id;
  }

  async function remove() {
    if (id) {
      if (!confirm(`Delete “${d.title || "this challenge"}” and every student's attempts at it?`)) return;
      const { error } = await api.DELETE("/api/v1/faculty/problems/{problem_id}", { params: { path: { problem_id: id } } });
      if (error) return toast(errorMessage(error), "error");
    }
    onDiscard();
  }

  async function tryIt() {
    const pid = await save();
    if (!pid) return;
    setRunning(true);
    setRunId(null);
    const { data, error } = await api.POST("/api/v1/faculty/problems/{problem_id}/test-run", {
      params: { path: { problem_id: pid } }, body: { language: refLang, code: ref },
    });
    if (error || !data) { setRunning(false); return toast(errorMessage(error), "error"); }
    setRunId(data.id);
  }

  const toggleLang = (l: Lang) => {
    const on = d.languages.includes(l);
    if (on && d.languages.length === 1) return;
    set({ languages: on ? d.languages.filter((x) => x !== l) : [...d.languages, l] });
  };

  return (
    <fieldset className="rounded border border-border">
      <button type="button" className="flex w-full items-center gap-3 px-3 py-2 text-left" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="font-medium">{d.title || "Untitled challenge"}</span>
        <Badge variant="secondary" className="capitalize">{d.level}</Badge>
        {!id && <Badge variant="warning">Not saved</Badge>}
        <span className="ml-auto text-sm text-muted-foreground">{open ? "Hide" : "Edit"}</span>
      </button>
      {open && (
        <div className="space-y-4 border-t border-border p-3 text-sm">
          <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
            <label className="space-y-1"><span className="font-medium">Title</span>
              <Input value={d.title} onChange={(e) => set({ title: e.target.value })} /></label>
            <label className="space-y-1"><span className="font-medium">Level</span>
              <NativeSelect value={d.level} onChange={(e) => set({ level: e.target.value as Draft["level"] })} className="w-full capitalize">
                {LEVELS.map((l) => <option key={l}>{l}</option>)}
              </NativeSelect></label>
          </div>
          <label className="block space-y-1"><span className="font-medium">Statement (Markdown)</span>
            <Textarea rows={7} value={d.statement} onChange={(e) => set({ statement: e.target.value })} placeholder={"Describe the task, the input format and the output format.\nUse `code` and ```fenced blocks``` as needed."} className="font-mono text-[13px]" /></label>
          {d.statement && <details><summary className="cursor-pointer text-muted-foreground">Preview</summary><div className="mt-2 rounded-md bg-muted p-3"><Rich>{d.statement}</Rich></div></details>}
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-medium">Languages</span>
            {ALL.map((l) => (
              <label key={l} className="flex items-center gap-1.5"><input type="checkbox" checked={d.languages.includes(l)} onChange={() => toggleLang(l)} />{LANG_LABEL[l]}</label>
            ))}
            <label className="ml-auto flex items-center gap-1.5">Time limit
              <Input type="number" min={200} max={5000} step={100} value={d.time_limit_ms} onChange={(e) => set({ time_limit_ms: Number(e.target.value) })} className="!w-24" /> ms</label>
            <label className="flex items-center gap-1.5">Memory
              <Input type="number" min={32} max={512} step={32} value={d.memory_mb} onChange={(e) => set({ memory_mb: Number(e.target.value) })} className="!w-20" /> MB</label>
          </div>
          <details>
            <summary className="cursor-pointer font-medium">Starter code (optional)</summary>
            <div className="mt-2 grid gap-3 sm:grid-cols-3">
              {d.languages.map((l) => (
                <label key={l} className="space-y-1"><span className="text-muted-foreground">{LANG_LABEL[l]}</span>
                  <Textarea rows={5} value={d.starter?.[l] ?? ""} onChange={(e) => set({ starter: { ...(d.starter ?? {}), [l]: e.target.value } })} className="font-mono text-xs" /></label>
              ))}
            </div>
          </details>

          <div className="space-y-2">
            <div className="flex items-center gap-3"><span className="mr-auto font-medium">Tests ({d.tests.length})</span>
              <Button onClick={() => set({ tests: [...d.tests, { input: "", expected: "", sample: false }] })} variant="outline" size="sm">+ Test</Button></div>
            {d.tests.map((t, i) => (
              <div key={i} className="grid items-start gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <Textarea aria-label={`Test ${i + 1} input`} rows={2} placeholder="Input (stdin)" value={t.input} onChange={(e) => setTest(i, { input: e.target.value })} className="font-mono text-xs" />
                <Textarea aria-label={`Test ${i + 1} expected output`} rows={2} placeholder="Expected output" value={t.expected} onChange={(e) => setTest(i, { expected: e.target.value })} className="font-mono text-xs" />
                <div className="flex flex-col gap-1.5">
                  <label className="flex items-center gap-1.5"><input type="checkbox" checked={t.sample} onChange={(e) => setTest(i, { sample: e.target.checked })} />Sample</label>
                  <Button disabled={d.tests.length === 1} onClick={() => set({ tests: d.tests.filter((_, j) => j !== i) })} variant="outline" size="sm">Remove</Button>
                </div>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">Output is compared ignoring trailing spaces and blank lines.</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button disabled={saving} onClick={() => void save()} size="sm">{saving ? "Saving…" : "Save challenge"}</Button>
            <Button onClick={remove} variant="outline" size="sm">{id ? "Delete" : "Discard"}</Button>
          </div>

          <details className="rounded-md border border-border p-3">
            <summary className="cursor-pointer font-medium">Check the tests with a reference solution</summary>
            <p className="my-2 text-muted-foreground">Runs your solution against every test, hidden ones included, and shows the full detail. Saves the challenge first.</p>
            <div className="mb-2 flex items-center gap-3">
              <NativeSelect value={refLang} onChange={(e) => setRefLang(e.target.value as Lang)} aria-label="Reference solution language" className="!w-auto">
                {d.languages.map((l) => <option key={l} value={l}>{LANG_LABEL[l]}</option>)}
              </NativeSelect>
              <Button disabled={running || !ref.trim()} onClick={tryIt} size="sm">{running ? "Running…" : "Run against all tests"}</Button>
            </div>
            <Editor value={ref} onChange={setRef} language={d.languages.includes(refLang) ? refLang : d.languages[0]} height="220px" label="Reference solution" />
            <div className="mt-3"><Results sub={sub} pending={running} /></div>
          </details>
        </div>
      )}
    </fieldset>
  );
}
