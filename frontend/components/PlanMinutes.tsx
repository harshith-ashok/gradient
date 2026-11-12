"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useToast } from "./Toast";

const OPTIONS = [30, 45, 60, 90, 120];

export function PlanMinutes({ courseId, value }: { courseId: string; value: number }) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  async function change(minutes: number) {
    setBusy(true);
    const { error } = await api.PUT("/api/v1/student/courses/{course_id}/plan", {
      params: { path: { course_id: courseId } },
      body: { minutes_per_day: minutes },
    });
    setBusy(false);
    if (error) return toast(errorMessage(error), "error");
    toast("Plan recalculated for your new daily study time.", "success");
    router.refresh();
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted">Daily study time</span>
      <select
        className="input !w-auto" value={value} disabled={busy}
        onChange={(e) => change(Number(e.target.value))}
      >
        {OPTIONS.map((m) => <option key={m} value={m}>{m} minutes</option>)}
      </select>
    </label>
  );
}
