"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useToast } from "../Toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function UploadForm() {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"file" | "text">("file");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    if (mode === "file") fd.delete("text");
    else fd.delete("file");
    setBusy(true);
    const { data, error } = await api.POST("/api/v1/faculty/syllabus", {
      body: {} as never,
      bodySerializer: () => fd,
    });
    setBusy(false);
    if (error || !data) return toast(errorMessage(error, "The upload failed. Check the file and try again."), "error");
    router.push(`/faculty/upload/${data.upload_id}`);
  }

  return (
    <form onSubmit={submit} className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10 p-6 max-w-2xl space-y-5">
      <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
        <label className="space-y-1.5 text-sm">
          <span className="font-medium">Course code</span>
          <Input name="course_code" required maxLength={24} placeholder="CS 330" />
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium">Course title</span>
          <Input name="course_title" required maxLength={200} placeholder="Databases" />
        </label>
      </div>
      <label className="block space-y-1.5 text-sm">
        <span className="font-medium">Department (optional)</span>
        <Input name="department" maxLength={120} />
      </label>
      <div role="tablist" className="flex gap-1 border-b border-border">
        {(["file", "text"] as const).map((m) => (
          <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
            className="-mb-px border-b-2 border-transparent px-4 py-2 text-sm font-medium text-muted-foreground aria-selected:border-primary aria-selected:text-primary">
            {m === "file" ? "Upload a file" : "Paste text"}
          </button>
        ))}
      </div>
      {mode === "file" ? (
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">Syllabus file</span>
          <Input name="file" type="file" required accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg" />
          <span className="text-xs text-muted-foreground">PDF, Word, text, or a photo or scan. Up to 20 MB.</span>
        </label>
      ) : (
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">Syllabus text</span>
          <Textarea name="text" required rows={10} placeholder="Paste the syllabus here" />
        </label>
      )}
      <Button disabled={busy}>{busy ? "Uploading…" : "Upload and analyse"}</Button>
    </form>
  );
}
