"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { Rich } from "../Rich";
import { useToast } from "../Toast";
import { Editor, LANG_LABEL, type Lang } from "./Editor";
import { Results } from "./Results";
import { useSubmission } from "./useSubmission";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";

type Problem = components["schemas"]["ProblemDetail"];
type Brief = components["schemas"]["SubmissionBrief"];

const DEFAULT_START: Record<Lang, string> = {
  c: "#include <stdio.h>\n\nint main(void) {\n    // read from stdin, write to stdout\n    return 0;\n}\n",
  cpp: "#include <iostream>\nusing namespace std;\n\nint main() {\n    // read from cin, write to cout\n    return 0;\n}\n",
  python: "# read from input(), write with print()\n",
};

const draftKey = (id: string, lang: string) => `gradient:draft:${id}:${lang}`;
const load = (id: string, lang: string): string | null => {
  try { return localStorage.getItem(draftKey(id, lang)); } catch { return null; }
};

export function ProblemSolver({ problem, history }: { problem: Problem; history: Brief[] }) {
  const toast = useToast();
  const langs = problem.languages as Lang[];
  const [lang, setLang] = useState<Lang>(langs[0]);
  const [code, setCode] = useState(problem.starter[langs[0]] ?? DEFAULT_START[langs[0]]);
  const [subId, setSubId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [solved, setSolved] = useState(problem.solved);
  const [past, setPast] = useState(history);
  const sub = useSubmission(subId, false, (s) => {
    setBusy(false);
    if (s.mode === "submit" && s.verdict === "accepted") setSolved(true);
    setPast((p) => [{ id: s.id, language: s.language, mode: s.mode, state: s.state, verdict: s.verdict, passed: s.passed, total: s.total, created_at: s.created_at }, ...p].slice(0, 10));
  });

  // Restore this problem's saved draft after load (kept out of the first render so the server and browser agree).
  useEffect(() => {
    const saved = load(problem.id, lang);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading browser storage can only happen after mount
    if (saved !== null) setCode(saved);
  }, [problem.id, lang]);

  function pick(next: Lang) {
    setLang(next);
    setCode(load(problem.id, next) ?? problem.starter[next] ?? DEFAULT_START[next]);
    setSubId(null);
  }
  function edit(v: string) {
    setCode(v);
    try { localStorage.setItem(draftKey(problem.id, lang), v); } catch { /* private mode: the draft just is not kept */ }
  }
  function reset() {
    if (!confirm("Discard your code and go back to the starting code?")) return;
    try { localStorage.removeItem(draftKey(problem.id, lang)); } catch { /* ignore */ }
    setCode(problem.starter[lang] ?? DEFAULT_START[lang]);
  }

  async function send(mode: "run" | "submit") {
    setBusy(true);
    setSubId(null);
    const { data, error } = await api.POST("/api/v1/student/problems/{problem_id}/submit", {
      params: { path: { problem_id: problem.id } }, body: { language: lang, code, mode },
    });
    if (error || !data) {
      setBusy(false);
      return toast(errorMessage(error), "error");
    }
    setSubId(data.id);
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <Card className="gap-0 p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="capitalize">{problem.level}</Badge>
          {solved && <Badge variant="success">Solved</Badge>}
          <span className="text-xs text-muted-foreground">{problem.time_limit_ms} ms · {problem.memory_mb} MB per test</span>
        </div>
        <Rich>{problem.statement}</Rich>
        <p className="text-sm text-muted-foreground">Read from standard input and print to standard output.</p>
        {problem.samples.map((s, i) => (
          <div key={i} className="grid gap-3 sm:grid-cols-2">
            <div><div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sample {i + 1} input</div>
              <pre className="overflow-auto rounded bg-muted p-2 font-mono text-xs">{s.input}</pre></div>
            <div><div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Expected output</div>
              <pre className="overflow-auto rounded bg-muted p-2 font-mono text-xs">{s.expected}</pre></div>
          </div>
        ))}
        <p className="text-xs text-muted-foreground">{problem.hidden_tests} more hidden {problem.hidden_tests === 1 ? "test is" : "tests are"} checked when you submit.</p>
      </Card>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium">Language</span>
            <NativeSelect value={lang} onChange={(e) => pick(e.target.value as Lang)} className="!w-auto">
              {langs.map((l) => <option key={l} value={l}>{LANG_LABEL[l]}</option>)}
            </NativeSelect>
          </label>
          <Button type="button" onClick={reset} variant="outline" size="sm" className="ml-auto">Reset code</Button>
        </div>
        <Editor value={code} onChange={edit} language={lang} label={`${LANG_LABEL[lang]} code editor`} />
        <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={busy} onClick={() => send("run")} variant="outline">Run samples</Button>
          <Button type="button" disabled={busy} onClick={() => send("submit")}>Submit</Button>
        </div>
        <Card className="gap-0 p-6"><Results sub={sub} pending={busy} />
          {!busy && !sub && <p className="text-sm text-muted-foreground">Run the samples to see how your code behaves. Submit when you are ready.</p>}
        </Card>
        {past.length > 0 && (
          <details className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10">
            <summary className="cursor-pointer px-4 py-3 text-sm font-medium">Your recent attempts</summary>
            <ul className="divide-y divide-border border-t border-border text-sm">
              {past.map((p) => (
                <li key={p.id} className="flex items-center gap-3 px-4 py-2">
                  <Badge variant={p.verdict === "accepted" ? "success" : "destructive"}>{p.verdict?.replace("_", " ") ?? p.state}</Badge>
                  <span>{LANG_LABEL[p.language]} · {p.mode === "run" ? "samples" : "submitted"} · {p.passed}/{p.total}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
        <p className="text-xs text-muted-foreground">
          Your code runs in an isolated sandbox with no internet access. <Link href={`/student/courses/${problem.course_id}/subtopics/${problem.subtopic_id}`} className="text-primary hover:underline">Back to {problem.subtopic_title}</Link>
        </p>
      </section>
    </div>
  );
}
