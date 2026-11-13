import type { components } from "@/lib/api-client/schema";
import type { Submission } from "./useSubmission";
import { Badge, type BadgeTone } from "@/components/ui/badge";

type Verdict = NonNullable<Submission["verdict"]>;
type TestVerdict = components["schemas"]["TestResult"]["verdict"];

export const VERDICT: Record<Verdict, { label: string; tone: BadgeTone; help?: string }> = {
  accepted: { label: "Accepted", tone: "success" },
  wrong_answer: { label: "Wrong answer", tone: "destructive", help: "Your program ran, but its output differs from what the test expects." },
  compile_error: { label: "Compilation error", tone: "destructive" },
  runtime_error: { label: "Runtime error", tone: "destructive", help: "Your program crashed or exited with an error." },
  time_limit: { label: "Time limit exceeded", tone: "warning", help: "Your program took too long. Look for an infinite loop or a slower approach." },
  output_limit: { label: "Too much output", tone: "warning" },
  internal_error: { label: "Runner problem", tone: "warning" },
};
const TEST: Record<TestVerdict, string> = {
  ok: "Passed", wrong_answer: "Wrong answer", runtime_error: "Runtime error", time_limit: "Time limit",
  output_limit: "Too much output", skipped: "Not run",
};

const Block = ({ label, text }: { label: string; text: string }) => (
  <div>
    <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
    <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-words rounded bg-muted p-2 font-mono text-xs">{text === "" ? "(empty)" : text}</pre>
  </div>
);

export function Results({ sub, pending }: { sub: Submission | null; pending: boolean }) {
  if (pending && (!sub || sub.state !== "done")) {
    return (
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
        {sub?.state === "queued" && sub.queue_position ? `Waiting for the code runner (${sub.queue_position} ahead)…` : "Running your code…"}
      </p>
    );
  }
  if (!sub?.verdict) return null;
  const v = VERDICT[sub.verdict];
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant={v.tone} className="h-6 px-3 text-sm">{v.label}</Badge>
        {sub.verdict !== "compile_error" && sub.verdict !== "internal_error" && (
          <span className="text-sm">
            <b>{sub.passed}</b> of <b>{sub.total}</b> {sub.mode === "run" ? "sample " : ""}tests passed
            {sub.runtime_ms != null && <span className="text-muted-foreground"> · slowest {sub.runtime_ms} ms</span>}
          </span>
        )}
        {sub.mode === "run" && sub.verdict === "accepted" && <span className="text-sm text-muted-foreground">Now press Submit to check the hidden tests.</span>}
      </div>
      {v.help && sub.verdict !== "accepted" && <p className="text-sm text-muted-foreground">{v.help}</p>}
      {sub.message && <p className="text-sm text-warning">{sub.message}</p>}
      {sub.compile_output && <Block label="Compiler output" text={sub.compile_output} />}
      <ul className="space-y-2">
        {sub.results.map((t) => (
          <li key={t.index} className="rounded-md border border-border">
            <details open={t.verdict !== "ok" && t.sample && t.verdict !== "skipped"}>
              <summary className="flex cursor-pointer flex-wrap items-center gap-2 px-3 py-2 text-sm">
                <Badge variant={t.verdict === "ok" ? "success" : t.verdict === "skipped" ? "secondary" : "destructive"}>{TEST[t.verdict]}</Badge>
                <span>{t.sample ? `Sample ${t.index + 1}` : `Test ${t.index + 1}`}{!t.sample && t.input == null ? " (hidden)" : ""}</span>
                <span className="ml-auto text-xs text-muted-foreground">{t.ms} ms</span>
              </summary>
              {t.input != null && (
                <div className="grid gap-3 border-t border-border p-3 sm:grid-cols-3">
                  <Block label="Input" text={t.input} />
                  <Block label="Expected" text={t.expected ?? ""} />
                  <Block label="Your output" text={t.stdout ?? ""} />
                  {t.stderr ? <div className="sm:col-span-3"><Block label="Error output" text={t.stderr} /></div> : null}
                </div>
              )}
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
