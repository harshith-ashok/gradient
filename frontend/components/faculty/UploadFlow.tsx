"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { useToast } from "../Toast";
import { stepText } from "./useJob";

type Upload = components["schemas"]["UploadOut"];
const BUSY = ["uploaded", "analyzing", "deriving"];

export function UploadFlow({ initial }: { initial: Upload }) {
  const router = useRouter();
  const toast = useToast();
  const [up, setUp] = useState(initial);
  const [picked, setPicked] = useState<Set<string>>(new Set(initial.topics?.map((t) => t.title)));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!BUSY.includes(up.status)) return;
    const id = setInterval(async () => {
      const { data } = await api.GET("/api/v1/faculty/syllabus/{upload_id}", { params: { path: { upload_id: up.id } } });
      if (!data) return;
      setUp(data);
      if (data.status === "topics_ready" && data.topics) setPicked((p) => (p.size ? p : new Set(data.topics!.map((t) => t.title))));
      if (data.status === "derived") router.push(`/faculty/courses/${data.course_id}?new=1`);
    }, 2000);
    return () => clearInterval(id);
  }, [up.status, up.id, router]);

  async function derive() {
    setBusy(true);
    const { error } = await api.POST("/api/v1/faculty/syllabus/{upload_id}/derive", {
      params: { path: { upload_id: up.id } },
      body: { topics: [...picked], replace: false },
    });
    setBusy(false);
    if (error) return toast(errorMessage(error), "error");
    setUp({ ...up, status: "deriving" });
  }

  if (up.status === "failed")
    return (
      <div className="card empty">
        <h3>We could not read this syllabus</h3>
        <p>{up.error ?? "Something went wrong while processing it."}</p>
        <Link href="/faculty/new" className="btn">Try again</Link>
      </div>
    );

  if (BUSY.includes(up.status))
    return (
      <div className="card card-pad max-w-2xl" role="status" aria-live="polite">
        <p className="font-serif text-lg font-semibold">
          {up.status === "deriving" ? "Drafting sub-topics" : "Reading your syllabus"}
        </p>
        <p className="mt-1 text-sm text-muted">{stepText(up.job ?? null, "Working…")}</p>
        <div className="mt-4 h-1.5 overflow-hidden rounded bg-ink-100"><div className="h-full w-1/3 animate-pulse rounded bg-crimson" /></div>
        <p className="mt-3 text-xs text-faint">This can take a minute or two. You can leave this page and come back from My courses.</p>
      </div>
    );

  const topics = up.topics ?? [];
  return (
    <div className="max-w-3xl space-y-4">
      {up.ocr_used && <p className="text-sm text-muted">Some pages were scanned, so the text was read with the vision model. Check the topics carefully.</p>}
      <ul className="card divide-y divide-line-soft">
        {topics.map((t) => (
          <li key={t.title}>
            <label className="flex cursor-pointer gap-3 px-5 py-3">
              <input type="checkbox" className="mt-1.5" checked={picked.has(t.title)}
                onChange={(e) => setPicked((p) => { const n = new Set(p); if (e.target.checked) n.add(t.title); else n.delete(t.title); return n; })} />
              <span><span className="font-medium">{t.title}</span><span className="block text-sm text-muted">{t.summary}</span></span>
            </label>
          </li>
        ))}
      </ul>
      <button className="btn btn-crimson" disabled={busy || picked.size === 0} onClick={derive}>
        Build {picked.size} {picked.size === 1 ? "topic" : "topics"} →
      </button>
    </div>
  );
}
