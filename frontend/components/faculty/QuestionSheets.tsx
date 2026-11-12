"use client";

import { useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { plural } from "@/lib/format";
import { useToast } from "../Toast";

type Report = components["schemas"]["QuestionImportReport"];
type Mode = Report["mode"];

/** Save a blob the browser just received as a file. */
function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function QuestionSheets({
  courseId, code, dirty, onSaveFirst, onImported,
}: {
  courseId: string;
  code: string;
  dirty: boolean;
  onSaveFirst: () => Promise<boolean>;
  onImported: () => void;
}) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("merge");
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState<"export" | "check" | "import" | null>(null);

  async function exportSheet(template: boolean) {
    setBusy("export");
    if (!template && dirty && !(await onSaveFirst())) return setBusy(null);
    const res = template
      ? await api.GET("/api/v1/faculty/questions/template.xlsx", { parseAs: "blob" })
      : await api.GET("/api/v1/faculty/courses/{course_id}/questions.xlsx", {
          params: { path: { course_id: courseId } }, parseAs: "blob",
        });
    setBusy(null);
    if (res.error || !res.data) return toast(errorMessage(res.error, "The download failed. Please try again."), "error");
    download(res.data as Blob, template ? "questions-template.xlsx" : `${code.replace(/[^A-Za-z0-9_-]+/g, "-")}-questions.xlsx`);
  }

  async function send(dryRun: boolean) {
    if (!file) return;
    setBusy(dryRun ? "check" : "import");
    if (!dryRun && dirty && !(await onSaveFirst())) return setBusy(null);
    const fd = new FormData();
    fd.set("file", file);
    fd.set("mode", mode);
    fd.set("dry_run", String(dryRun));
    const { data, error } = await api.POST("/api/v1/faculty/courses/{course_id}/questions/import", {
      params: { path: { course_id: courseId } }, body: {} as never, bodySerializer: () => fd,
    });
    setBusy(null);
    if (error || !data) return toast(errorMessage(error, "The file could not be read."), "error");
    setReport(data);
    if (data.saved) {
      toast(`Imported: ${plural(data.added, "question")} added, ${data.updated} updated${data.removed ? `, ${data.removed} removed` : ""}.`, "success");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      onImported();
    }
  }

  const changes = report ? report.added + report.updated + report.removed : 0;
  const ready = report && !report.saved && report.dry_run && report.total_errors === 0;

  return (
    <details className="card">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium">Import or export questions (Excel)</summary>
      <div className="space-y-5 border-t border-line-soft p-4 text-sm">
        <div>
          <p className="mb-2 text-muted">
            Export every quiz question of this course to a sheet, edit it in Excel, and import it back. Rows keep a
            Question ID so edits update the same question instead of duplicating it.
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy !== null} onClick={() => exportSheet(false)}>
              {busy === "export" ? "Preparing…" : "Export questions (.xlsx)"}
            </button>
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy !== null} onClick={() => exportSheet(true)}>
              Blank template
            </button>
          </div>
        </div>

        <div className="space-y-3 border-t border-line-soft pt-4">
          <label className="block space-y-1.5">
            <span className="font-medium">Excel file to import</span>
            <input
              ref={fileRef} type="file" accept=".xlsx" className="input"
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); setReport(null); }}
            />
          </label>
          <fieldset className="space-y-1.5">
            <legend className="font-medium">What should happen to questions already in the course?</legend>
            {([
              ["merge", "Add and update", "New rows are added; rows with a Question ID update that question. Nothing is deleted."],
              ["replace", "Replace", "Each sub-topic in the file ends up with exactly the questions in the file. Others are removed."],
            ] as const).map(([v, label, help]) => (
              <label key={v} className="flex items-start gap-2">
                <input type="radio" name="import-mode" className="mt-1" checked={mode === v} onChange={() => { setMode(v); setReport(null); }} />
                <span><b>{label}</b><span className="block text-muted">{help}</span></span>
              </label>
            ))}
          </fieldset>
          {dirty && <p className="text-warn">You have unsaved edits. They will be saved before the import so nothing is overwritten.</p>}
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary btn-sm" disabled={!file || busy !== null} onClick={() => send(true)}>
              {busy === "check" ? "Checking…" : "Check file"}
            </button>
            <button type="button" className="btn btn-crimson btn-sm" disabled={!ready || !changes || busy !== null} onClick={() => send(false)}>
              {busy === "import" ? "Importing…" : changes ? `Import ${plural(changes, "change")}` : "Import"}
            </button>
          </div>
        </div>

        {report && <ReportView report={report} />}
      </div>
    </details>
  );
}

function ReportView({ report }: { report: Report }) {
  const bad = report.total_errors > 0;
  return (
    <div role="status" aria-live="polite" className="space-y-3 rounded-md border border-line-soft bg-ink-50 p-4">
      {bad ? (
        <p className="font-medium text-bad">
          {plural(report.total_errors, "problem")} found. Nothing was imported. Fix the sheet and check it again.
        </p>
      ) : (
        <p className="font-medium">
          {report.saved ? "Imported." : "The file is valid. This is what importing will do:"}{" "}
          <span className="font-normal">
            {report.added} added · {report.updated} updated · {report.removed} removed · {report.unchanged} unchanged · {report.skipped} skipped
          </span>
        </p>
      )}
      {bad && (
        <ul className="max-h-60 space-y-1 overflow-auto">
          {report.errors.map((e, i) => <li key={i}><b>Row {e.row}:</b> {e.message}</li>)}
          {report.total_errors > report.errors.length && <li className="text-muted">…and {report.total_errors - report.errors.length} more.</li>}
        </ul>
      )}
      {!bad && report.subtopics.length > 0 && (
        <table className="table">
          <thead><tr><th>Sub-topic</th><th className="num">Added</th><th className="num">Updated</th><th className="num">Removed</th></tr></thead>
          <tbody>
            {report.subtopics.map((s, i) => (
              <tr key={i}><td>{s.topic} › {s.subtopic}</td><td className="num">{s.added}</td><td className="num">{s.updated}</td><td className={`num ${s.removed ? "text-bad" : ""}`}>{s.removed}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {report.warnings.length > 0 && (
        <ul className="space-y-1 text-muted">{report.warnings.slice(0, 10).map((w, i) => <li key={i}>{w}</li>)}</ul>
      )}
    </div>
  );
}
