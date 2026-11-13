"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { useToast } from "../Toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type Issue = components["schemas"]["IssueDetail"];
const TONE = { open: "destructive", resolved: "success", ignored: "secondary" } as const;

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
    <Card className="gap-0 p-6 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted-foreground">Status</span>
        <Badge variant={TONE[issue.status]}>{issue.status}</Badge>
        <div className="ml-auto flex gap-2">
          {issue.status !== "resolved" && (
            <Button type="button" disabled={busy} onClick={() => save({ status: "resolved" }, "Marked as resolved. It reopens if it happens again.")} size="sm">Mark resolved</Button>
          )}
          {issue.status !== "ignored" && (
            <Button type="button" disabled={busy} onClick={() => save({ status: "ignored" }, "Ignored.")} variant="outline" size="sm">Ignore</Button>
          )}
          {issue.status !== "open" && (
            <Button type="button" disabled={busy} onClick={() => save({ status: "open" }, "Reopened.")} variant="outline" size="sm">Reopen</Button>
          )}
        </div>
      </div>
      <div>
        <label htmlFor="note" className="mb-1 block text-sm font-semibold">Note</label>
        <Textarea id="note" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What you found, or the fix" />
        <Button type="button" disabled={busy || note === (issue.note ?? "")} onClick={() => save({ note }, "Note saved.")} variant="outline" size="sm" className="mt-2">Save note</Button>
      </div>
    </Card>
  );
}
