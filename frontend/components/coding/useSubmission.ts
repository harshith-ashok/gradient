"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";

export type Submission = components["schemas"]["SubmissionOut"];

/** Poll a submission until it is done. `staff` reads through the faculty endpoint (full test detail). */
export function useSubmission(id: string | null, staff: boolean, onDone?: (s: Submission) => void) {
  const [sub, setSub] = useState<Submission | null>(null);
  const done = useRef(onDone);
  useEffect(() => {
    done.current = onDone;
  });
  useEffect(() => {
    if (!id) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      const { data } = staff
        ? await api.GET("/api/v1/faculty/submissions/{submission_id}", { params: { path: { submission_id: id } } })
        : await api.GET("/api/v1/student/submissions/{submission_id}", { params: { path: { submission_id: id } } });
      if (stop) return;
      if (data) setSub(data);
      if (!data || data.state !== "done") timer = setTimeout(tick, 600);
      else done.current?.(data);
    };
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id, staff]);
  return id ? sub : null;
}
