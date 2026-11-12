"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";

export type Job = components["schemas"]["JobOut"];

/** Poll a background job every 2 seconds until it succeeds or fails. */
export function useJob(jobId: string | null, onDone?: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const done = useRef(onDone);
  useEffect(() => {
    done.current = onDone;
  });
  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      const { data } = await api.GET("/api/v1/jobs/{job_id}", { params: { path: { job_id: jobId } } });
      if (stop) return;
      if (data) setJob(data);
      if (!data || data.status === "queued" || data.status === "running") timer = setTimeout(tick, 2000);
      else done.current?.(data);
    };
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [jobId]);
  return jobId ? job : null;
}

export const stepText = (job: Job | null, fallback: string) => {
  const p = job?.progress as { step?: string; done?: number; total?: number } | undefined;
  if (!p?.step) return job?.status === "queued" ? "Waiting for the AI worker…" : fallback;
  return p.total ? `${p.step} (${p.done ?? 0} of ${p.total})` : p.step;
};
