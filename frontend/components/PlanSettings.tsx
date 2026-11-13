"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useToast } from "./Toast";
import { NativeSelect } from "@/components/ui/native-select";

const MINUTES = [30, 45, 60, 90, 120];
const DAYS = [7, 14, 21, 30, 45, 60, 90];

export function PlanSettings({
  courseId, minutes, days, planning,
}: { courseId: string; minutes: number; days: number; planning: boolean }) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  // While the AI planner is still working, check back until it is done.
  useEffect(() => {
    if (!planning) return;
    const id = setInterval(() => router.refresh(), 4000);
    return () => clearInterval(id);
  }, [planning, router]);

  async function change(body: { minutes_per_day?: number; target_days?: number }) {
    setBusy(true);
    const { error } = await api.PUT("/api/v1/student/courses/{course_id}/plan", {
      params: { path: { course_id: courseId } },
      body,
    });
    setBusy(false);
    if (error) return toast(errorMessage(error), "error");
    toast("Plan recalculated for your new daily study time.", "success");
    router.refresh();
  }

  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <label className="flex items-center gap-2">
        <span className="text-muted-foreground">Finish within</span>
        <NativeSelect value={days} disabled={busy} onChange={(e) => change({ target_days: Number(e.target.value) })} className="!w-auto">
          {DAYS.map((d) => <option key={d} value={d}>{d} days</option>)}
        </NativeSelect>
      </label>
      <label className="flex items-center gap-2">
        <span className="text-muted-foreground">Daily study time</span>
        <NativeSelect value={minutes} disabled={busy} onChange={(e) => change({ minutes_per_day: Number(e.target.value) })} className="!w-auto">
          {MINUTES.map((m) => <option key={m} value={m}>{m} minutes</option>)}
        </NativeSelect>
      </label>
    </div>
  );
}
