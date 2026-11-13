import Link from "next/link";
import type { components } from "@/lib/api-client/schema";
import { TASK_LABEL, TASK_TONE, relDay, taskHref } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";

type Task = components["schemas"]["TaskOut"];

export function TaskRow({
  task, courseId, showDate = false, showCourse, locked = false, today,
}: { task: Task; courseId: string; showDate?: boolean; showCourse?: string; locked?: boolean; today?: string }) {
  return (
    <div className={`task ${task.done ? "done" : ""}`}>
      <span className="tick" aria-hidden="true">{task.done ? "✓" : ""}</span>
      <div className="min-w-0 flex-1">
        <div className="t-title">{task.title}</div>
        <div className="t-meta">
          {showCourse && <>{showCourse} · </>}
          {showDate && <>{relDay(task.date, today)} · </>}
          {task.minutes} min
          {task.done && task.result && <> · {task.result}</>}
        </div>
        {task.note && !task.done && <div className="t-meta italic">{task.note}</div>}
      </div>
      <Badge variant={TASK_TONE[task.type] ?? "secondary"}>{TASK_LABEL[task.type]}</Badge>
      {!task.done && !locked && (
        <Link href={taskHref(courseId, task)} className={buttonVariants({ variant: "outline", size: "sm" })}>Open →</Link>
      )}
    </div>
  );
}
