"use client";

import Link from "next/link";
import { useState } from "react";
import type { components } from "@/lib/api-client/schema";
import { EnrollmentProgress } from "./EnrollmentProgress";

type Enr = components["schemas"]["EnrollmentDetail"];

export function ProgressTabs({ enrollments }: { enrollments: Enr[] }) {
  const [sel, setSel] = useState(enrollments[0]?.course_id);
  const current = enrollments.find((e) => e.course_id === sel) ?? enrollments[0];
  return (
    <>
      {enrollments.length > 1 && (
        <div role="tablist" className="mb-5 flex flex-wrap gap-1 border-b border-line">
          {enrollments.map((e) => (
            <button
              key={e.course_id} role="tab" type="button" aria-selected={current.course_id === e.course_id}
              onClick={() => setSel(e.course_id)}
              className="-mb-px border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted hover:text-ink-900 aria-selected:border-crimson aria-selected:text-crimson"
            >
              {e.code} · {e.title}
            </button>
          ))}
        </div>
      )}
      <EnrollmentProgress
        e={current}
        actions={<Link href={`/student/courses/${current.course_id}/plan`} className="btn btn-secondary">Study plan</Link>}
      />
    </>
  );
}
