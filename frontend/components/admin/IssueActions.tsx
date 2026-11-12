"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { useToast } from "../Toast";

type Issue = components["schemas"]["IssueDetail"];
const TONE = { open: "badge-bad", resolved: "badge-ok", ignored: "badge-info" } as const;

export function IssueActions({ issue }: { issue: Issue }) {
  const router = useRouter();
  const toast = useToast();
  const [note, setNote] = useState(issue.note ?? "");
  const [busy, setBusy] = useState(false);

  async function save(body: { status?: Issue["status"]; note?: string }, done: string) {
    setBusy(true);
    const { error } = await api.PUT("/api/v1/admin/issues/{issue_id}", { params: { path: { issue_id: issue.id } }, body });
    setBusy(false);
    if (error) return toast(errorMessage(error), "error");
    toast(done, "success");
    router.refresh();
  }

  return (
    <div className="card card-pad space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted">Status</span>
        <span className={`badge ${TONE[issue.status]}`}>{issue.status}</span>
        <div className="ml-auto flex gap-2">
          {issue.status !== "resolved" && (
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => save({ status: "resolved" }, "Marked as resolved. It reopens if it happens again.")}>Mark resolved</button>
          )}
          {issue.status !== "ignored" && (
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => save({ status: "ignored" }, "Ignored.")}>Ignore</button>
          )}
          {issue.status !== "open" && (
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => save({ status: "open" }, "Reopened.")}>Reopen</button>
          )}
        </div>
      </div>
      <div>
        <label htmlFor="note" className="mb-1 block text-sm font-semibold">Note</label>
        <textarea id="note" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} className="input" placeholder="What you found, or the fix" />
        <button type="button" className="btn btn-secondary btn-sm mt-2" disabled={busy || note === (issue.note ?? "")} onClick={() => save({ note }, "Note saved.")}>Save note</button>
      </div>
    </div>
  );
}
